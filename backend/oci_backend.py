import base64
import hashlib
import logging
import os
import re
import time
import weakref
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _load_cache_ttl_seconds() -> int:
    raw_value = (os.getenv("OCI_LIST_CACHE_TTL_SECONDS", "300") or "300").strip()
    try:
        return max(0, int(raw_value))
    except (TypeError, ValueError):
        logger.warning("Invalid OCI_LIST_CACHE_TTL_SECONDS value '%s'; falling back to 300 seconds", raw_value)
        return 300


OCI_LIST_CACHE_TTL_SECONDS = _load_cache_ttl_seconds()
_OCI_LIST_CACHE: Dict[str, Dict[str, Any]] = {}
_OCI_LIST_CACHE_LOCK = Lock()
_OCI_LIST_KEY_LOCKS: "weakref.WeakValueDictionary[str, Lock]" = weakref.WeakValueDictionary()


def _require_oci_sdk():
    try:
        import oci  # type: ignore
        from oci.pagination import list_call_get_all_results  # type: ignore
    except ImportError as exc:
        raise RuntimeError("OCI SDK is not installed") from exc
    return oci, list_call_get_all_results


def _is_truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_env(prefix: str, suffix: str) -> str:
    return os.getenv(f"OCI_{prefix}_{suffix}", "").strip()


def _normalize_private_key(prefix: str) -> str:
    key_b64 = _safe_env(prefix, "PRIVATE_KEY_B64")
    if key_b64:
        normalized_b64_value = key_b64.replace("\\n", "\n").strip()
        if "-----BEGIN" in normalized_b64_value:
            return normalized_b64_value
        try:
            compact_b64 = re.sub(r"\s+", "", key_b64)
            padded_b64 = compact_b64 + ("=" * (-len(compact_b64) % 4))
            return base64.b64decode(padded_b64, validate=False).decode("utf-8").strip()
        except Exception as exc:
            raw_key_fallback = os.getenv(f"OCI_{prefix}_PRIVATE_KEY", "")
            if raw_key_fallback.strip():
                logger.warning(
                    "OCI_%s_PRIVATE_KEY_B64 could not be decoded; falling back to OCI_%s_PRIVATE_KEY",
                    prefix,
                    prefix,
                )
                return raw_key_fallback.replace("\\n", "\n").strip()
            raise RuntimeError(f"Invalid base64 private key for OCI tenancy '{prefix.lower()}': {exc}") from exc

    raw_key = os.getenv(f"OCI_{prefix}_PRIVATE_KEY", "")
    return raw_key.replace("\\n", "\n").strip()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip()).strip("_").upper()


def _normalize_fingerprint(value: str) -> Optional[str]:
    if not str(value or "").strip():
        return None
    raw = re.sub(r"[^0-9a-fA-F]", "", str(value or ""))
    if len(raw) != 32:
        logger.warning("OCI fingerprint has invalid format; expected 32 hex chars after normalization")
        return None
    raw = raw.lower()
    return ":".join(raw[index : index + 2] for index in range(0, 32, 2))


def _derive_fingerprint_from_private_key(private_key: str, pass_phrase: Optional[str]) -> Optional[str]:
    if not private_key:
        return None
    try:
        from cryptography.hazmat.primitives import serialization  # type: ignore

        passphrase_bytes = pass_phrase.encode("utf-8") if pass_phrase else None
        key = serialization.load_pem_private_key(
            private_key.encode("utf-8"),
            passphrase_bytes,
        )
        public_key_der = key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        digest = hashlib.md5(public_key_der).hexdigest()  # nosec B324 - OCI API key fingerprint requires MD5
        return ":".join(digest[index : index + 2] for index in range(0, 32, 2))
    except Exception as exc:
        logger.warning("Unable to derive OCI fingerprint from private key content: %s", exc)
        return None


def _mask_fingerprint(value: Optional[str]) -> str:
    fingerprint = str(value or "").strip()
    if not fingerprint:
        return ""
    compact = re.sub(r"[^0-9a-fA-F]", "", fingerprint).lower()
    if len(compact) < 8:
        return "***"
    return f"***{compact[-8:]}"


def _mask_identifier(value: Optional[str]) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 8:
        return "***"
    return f"***{raw[-8:]}"


def _cached_tenancy_list(cache_key: str, loader: Callable[[], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if OCI_LIST_CACHE_TTL_SECONDS <= 0:
        return loader()

    def _read_cache(now_value: float) -> Optional[List[Dict[str, Any]]]:
        with _OCI_LIST_CACHE_LOCK:
            cached = _OCI_LIST_CACHE.get(cache_key)
            if cached and now_value - float(cached.get("cached_at", 0)) < OCI_LIST_CACHE_TTL_SECONDS:
                return cached.get("value", [])
        return None

    now = time.monotonic()
    cached_value = _read_cache(now)
    if cached_value is not None:
        return cached_value

    with _OCI_LIST_CACHE_LOCK:
        key_lock = _OCI_LIST_KEY_LOCKS.get(cache_key)
        if not key_lock:
            key_lock = Lock()
            _OCI_LIST_KEY_LOCKS[cache_key] = key_lock

    with key_lock:
        now = time.monotonic()
        cached_value = _read_cache(now)
        if cached_value is not None:
            return cached_value
        value = loader()
        with _OCI_LIST_CACHE_LOCK:
            _OCI_LIST_CACHE[cache_key] = {"cached_at": time.monotonic(), "value": value}
        return value


@dataclass(frozen=True)
class OciTenancyConfig:
    key: str
    display_name: str
    tenancy_ocid: str
    user_ocid: str
    fingerprint: str
    private_key: str
    region: str
    image_compartment_ocid: str
    pass_phrase: Optional[str] = None
    fallback_fingerprint: Optional[str] = None

    def sdk_config(self, fingerprint_override: Optional[str] = None) -> Dict[str, str]:
        active_fingerprint = (fingerprint_override or self.fingerprint).strip()
        return {
            "user": self.user_ocid,
            "fingerprint": active_fingerprint,
            "tenancy": self.tenancy_ocid,
            "region": self.region,
            "key_content": self.private_key,
        }

    def signer(self, fingerprint_override: Optional[str] = None):
        oci, _ = _require_oci_sdk()
        active_fingerprint = (fingerprint_override or self.fingerprint).strip()
        return oci.signer.Signer(
            self.tenancy_ocid,
            self.user_ocid,
            active_fingerprint,
            None,
            private_key_content=self.private_key,
            pass_phrase=self.pass_phrase,
        )

    def summary(self) -> Dict[str, str]:
        return {
            "key": self.key,
            "name": self.display_name,
            "region": self.region,
            "tenancy_ocid": self.tenancy_ocid,
            "image_compartment_ocid": self.image_compartment_ocid,
        }


@lru_cache(maxsize=1)
def get_configured_tenancies() -> Dict[str, OciTenancyConfig]:
    tenancies: Dict[str, OciTenancyConfig] = {}
    tenancy_keys = [item.strip() for item in os.getenv("OCI_TENANCY_KEYS", "").split(",") if item.strip()]
    for raw_key in tenancy_keys:
        prefix = _normalize_key(raw_key)
        display_name = _safe_env(prefix, "DISPLAY_NAME") or raw_key
        tenancy_ocid = _safe_env(prefix, "TENANCY_OCID")
        user_ocid = _safe_env(prefix, "USER_OCID")
        configured_fingerprint = _normalize_fingerprint(_safe_env(prefix, "FINGERPRINT"))
        try:
            private_key = _normalize_private_key(prefix)
        except Exception as exc:
            logger.warning("Skipping OCI tenancy '%s' because the private key could not be parsed: %s", raw_key, exc)
            continue
        region = _safe_env(prefix, "REGION")
        image_compartment_ocid = _safe_env(prefix, "IMAGE_COMPARTMENT_OCID") or tenancy_ocid
        pass_phrase = os.getenv(f"OCI_{prefix}_PRIVATE_KEY_PASSPHRASE", "") or None
        derived_fingerprint = _derive_fingerprint_from_private_key(private_key, pass_phrase)
        fingerprint = configured_fingerprint
        fallback_fingerprint: Optional[str] = None
        fingerprint_source = "configured"
        if derived_fingerprint:
            if configured_fingerprint and configured_fingerprint != derived_fingerprint:
                logger.warning(
                    "OCI tenancy '%s' fingerprint does not match private key; using derived fingerprint from key content",
                    raw_key,
                )
                fallback_fingerprint = configured_fingerprint
            fingerprint = derived_fingerprint
            fingerprint_source = "derived"
        elif configured_fingerprint:
            logger.warning(
                "OCI tenancy '%s' could not derive fingerprint from key content; using configured fingerprint value",
                raw_key,
            )

        required = {
            "TENANCY_OCID": tenancy_ocid,
            "USER_OCID": user_ocid,
            "FINGERPRINT": fingerprint,
            "PRIVATE_KEY": private_key,
            "REGION": region,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            logger.warning("Skipping OCI tenancy '%s' because these env vars are missing: %s", raw_key, ", ".join(missing))
            continue
        logger.info(
            "OCI tenancy '%s' signer context prepared: user_ocid_suffix=%s tenancy_ocid_suffix=%s region=%s effective_fingerprint_suffix=%s fingerprint_source=%s",
            raw_key,
            _mask_identifier(user_ocid),
            _mask_identifier(tenancy_ocid),
            region,
            _mask_fingerprint(fingerprint),
            fingerprint_source,
        )

        tenancies[raw_key] = OciTenancyConfig(
            key=raw_key,
            display_name=display_name,
            tenancy_ocid=tenancy_ocid,
            user_ocid=user_ocid,
            fingerprint=fingerprint,
            private_key=private_key,
            region=region,
            image_compartment_ocid=image_compartment_ocid,
            pass_phrase=pass_phrase,
            fallback_fingerprint=fallback_fingerprint,
        )
    return tenancies


def is_oci_enabled() -> bool:
    enabled_value = os.getenv("OCI_ENABLED")
    if enabled_value is not None and str(enabled_value).strip():
        return _is_truthy(enabled_value) and bool(get_configured_tenancies())
    return bool(get_configured_tenancies())


def list_tenancy_summaries() -> List[Dict[str, str]]:
    return [cfg.summary() for cfg in get_configured_tenancies().values()]


def get_tenancy_config(tenancy_key: str) -> OciTenancyConfig:
    config = get_configured_tenancies().get(tenancy_key)
    if not config:
        raise ValueError(f"Unknown OCI tenancy '{tenancy_key}'")
    return config


def _client_bundle(tenancy_key: str, *, use_fallback_fingerprint: bool = False):
    oci, _ = _require_oci_sdk()
    config = get_tenancy_config(tenancy_key)
    fingerprint_override = config.fallback_fingerprint if use_fallback_fingerprint else None
    signer = config.signer(fingerprint_override=fingerprint_override)
    sdk_config = config.sdk_config(fingerprint_override=fingerprint_override)
    oci.config.validate_config(sdk_config)
    return config, oci.identity.IdentityClient(sdk_config, signer=signer), oci.core.ComputeClient(sdk_config, signer=signer), oci.core.VirtualNetworkClient(sdk_config, signer=signer)


def _is_oci_not_authenticated_error(exc: Exception) -> bool:
    return int(getattr(exc, "status", 0) or 0) == 401 and str(getattr(exc, "code", "") or "") == "NotAuthenticated"


def _run_with_fingerprint_fallback(tenancy_key: str, operation: Callable[[OciTenancyConfig, Any, Any, Any], Any]) -> Any:
    """Execute an OCI SDK operation and retry once with configured fingerprint on OCI 401 auth errors."""
    config, identity_client, compute_client, network_client = _client_bundle(tenancy_key)
    try:
        return operation(config, identity_client, compute_client, network_client)
    except Exception as exc:
        if not (_is_oci_not_authenticated_error(exc) and config.fallback_fingerprint):
            raise
        logger.warning(
            "OCI auth failed for tenancy '%s' with derived fingerprint; retrying once with configured fingerprint (masked=%s)",
            tenancy_key,
            _mask_fingerprint(config.fallback_fingerprint),
        )
        fallback_config, fallback_identity, fallback_compute, fallback_network = _client_bundle(
            tenancy_key,
            use_fallback_fingerprint=True,
        )
        return operation(fallback_config, fallback_identity, fallback_compute, fallback_network)


def list_availability_domains(tenancy_key: str) -> List[Dict[str, str]]:
    _, list_call_get_all_results = _require_oci_sdk()
    response = _run_with_fingerprint_fallback(
        tenancy_key,
        lambda config, identity_client, _compute_client, _network_client: list_call_get_all_results(
            identity_client.list_availability_domains,
            compartment_id=config.tenancy_ocid,
        ),
    )
    return [{"name": item.name} for item in response.data if getattr(item, "name", None)]


def list_compartments(tenancy_key: str) -> List[Dict[str, str]]:
    def _load() -> List[Dict[str, str]]:
        started_at = time.perf_counter()
        _, list_call_get_all_results = _require_oci_sdk()
        response = _run_with_fingerprint_fallback(
            tenancy_key,
            lambda active_config, identity_client, _compute_client, _network_client: list_call_get_all_results(
                identity_client.list_compartments,
                compartment_id=active_config.tenancy_ocid,
                compartment_id_in_subtree=True,
                access_level="ANY",
                lifecycle_state="ACTIVE",
            ),
        )
        config = get_tenancy_config(tenancy_key)
        active_items = []
        raw_by_id: Dict[str, Dict[str, str]] = {
            config.tenancy_ocid: {
                "id": config.tenancy_ocid,
                "name": f"{config.display_name} (root)",
                "parent_id": "",
            }
        }
        for item in response.data:
            # Keep this defensive check even though lifecycle_state=ACTIVE is passed in the SDK call.
            lifecycle_state = str(getattr(item, "lifecycle_state", "") or "").upper()
            if lifecycle_state != "ACTIVE":
                continue
            if item.id == config.tenancy_ocid:
                continue
            row = {
                "id": item.id,
                "name": item.name or item.id,
                "parent_id": item.compartment_id or "",
            }
            raw_by_id[item.id] = row
            active_items.append(row)

        path_cache: Dict[str, str] = {}

        def build_path(compartment_id: str) -> str:
            cached_path = path_cache.get(compartment_id)
            if cached_path is not None:
                return cached_path
            cursor = raw_by_id.get(compartment_id)
            parts: List[str] = []
            seen = set()
            while cursor and cursor["id"] not in seen:
                seen.add(cursor["id"])
                parts.append(cursor["name"])
                parent_id = cursor.get("parent_id")
                if not parent_id:
                    break
                parent = raw_by_id.get(parent_id)
                cursor = parent
                if parent_id == config.tenancy_ocid and parent:
                    parts.append(parent["name"])
                    break
            path = " / ".join(reversed(parts))
            path_cache[compartment_id] = path
            return path

        result = []
        for item in active_items:
            result.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "path": build_path(item["id"]),
                    "parent_id": item["parent_id"],
                }
            )
        result.sort(key=lambda item: item["path"].lower())
        logger.info(
            "Loaded %d OCI compartments for tenancy '%s' in %.2fs",
            len(result),
            tenancy_key,
            time.perf_counter() - started_at,
        )
        return result

    return _cached_tenancy_list(f"compartments:{tenancy_key}", _load)


def list_vcns(tenancy_key: str, compartment_id: str) -> List[Dict[str, str]]:
    _, list_call_get_all_results = _require_oci_sdk()
    response = _run_with_fingerprint_fallback(
        tenancy_key,
        lambda _config, _identity_client, _compute_client, network_client: list_call_get_all_results(
            network_client.list_vcns,
            compartment_id=compartment_id,
            lifecycle_state="AVAILABLE",
        ),
    )
    results = []
    for item in response.data:
        cidrs = list(getattr(item, "cidr_blocks", None) or [])
        if not cidrs and getattr(item, "cidr_block", None):
            cidrs = [item.cidr_block]
        results.append(
            {
                "id": item.id,
                "name": item.display_name or item.id,
                "cidr_blocks": ", ".join(cidrs),
            }
        )
    results.sort(key=lambda item: item["name"].lower())
    return results


def list_subnets(tenancy_key: str, compartment_id: str, vcn_id: str) -> List[Dict[str, Any]]:
    _, list_call_get_all_results = _require_oci_sdk()
    response = _run_with_fingerprint_fallback(
        tenancy_key,
        lambda _config, _identity_client, _compute_client, network_client: list_call_get_all_results(
            network_client.list_subnets,
            compartment_id=compartment_id,
            vcn_id=vcn_id,
            lifecycle_state="AVAILABLE",
        ),
    )
    results = []
    for item in response.data:
        results.append(
            {
                "id": item.id,
                "name": item.display_name or item.id,
                "cidr_block": getattr(item, "cidr_block", "") or "",
                "availability_domain": getattr(item, "availability_domain", "") or "",
                "prohibit_public_ip_on_vnic": bool(getattr(item, "prohibit_public_ip_on_vnic", False)),
            }
        )
    results.sort(key=lambda item: item["name"].lower())
    return results


def list_nsgs(tenancy_key: str, compartment_id: str, vcn_id: str) -> List[Dict[str, str]]:
    _, list_call_get_all_results = _require_oci_sdk()
    response = _run_with_fingerprint_fallback(
        tenancy_key,
        lambda _config, _identity_client, _compute_client, network_client: list_call_get_all_results(
            network_client.list_network_security_groups,
            compartment_id=compartment_id,
            vcn_id=vcn_id,
        ),
    )
    results = [
        {
            "id": item.id,
            "name": item.display_name or item.id,
        }
        for item in response.data
    ]
    results.sort(key=lambda item: item["name"].lower())
    return results


def list_images(tenancy_key: str, compartment_id: Optional[str] = None) -> List[Dict[str, str]]:
    _, list_call_get_all_results = _require_oci_sdk()
    target_compartment = (compartment_id or get_tenancy_config(tenancy_key).image_compartment_ocid).strip()
    response = _run_with_fingerprint_fallback(
        tenancy_key,
        lambda active_config, _identity_client, compute_client, _network_client:
            list_call_get_all_results(
                compute_client.list_images,
                compartment_id=target_compartment or active_config.image_compartment_ocid,
                lifecycle_state="AVAILABLE",
                sort_by="TIMECREATED",
                sort_order="DESC",
            ),
    )
    results = []
    for item in response.data:
        if target_compartment and getattr(item, "compartment_id", None) != target_compartment:
            continue
        results.append(
            {
                "id": item.id,
                "name": item.display_name or item.id,
                "operating_system": getattr(item, "operating_system", "") or "",
                "operating_system_version": getattr(item, "operating_system_version", "") or "",
            }
        )
    results.sort(key=lambda item: item["name"].lower())
    return results


def list_shapes(tenancy_key: str, compartment_id: str, image_id: Optional[str] = None) -> List[Dict[str, Any]]:
    _, list_call_get_all_results = _require_oci_sdk()
    def _load_shapes(active_image_id: Optional[str]):
        kwargs: Dict[str, Any] = {"compartment_id": compartment_id}
        if active_image_id:
            kwargs["image_id"] = active_image_id
        return _run_with_fingerprint_fallback(
            tenancy_key,
            lambda _config, _identity_client, compute_client, _network_client: list_call_get_all_results(
                compute_client.list_shapes,
                **kwargs,
            ),
        )

    try:
        response = _load_shapes(image_id)
    except Exception as exc:
        status = int(getattr(exc, "status", 0) or 0)
        code = str(getattr(exc, "code", "") or "")
        retriable_codes = {"NotAuthorizedOrNotFound", "InvalidParameter", "InvalidParameterValue", "NotAuthenticated"}
        if image_id and (status in {400, 401, 403, 404} or code in retriable_codes):
            logger.warning(
                "OCI shape lookup failed with image filter for tenancy '%s' compartment '%s' (status=%s code=%s); retrying without image_id",
                tenancy_key,
                compartment_id,
                status,
                code,
            )
            response = _load_shapes(None)
        else:
            raise
    results = []
    for item in response.data:
        shape_name = getattr(item, "shape", "") or ""
        if not shape_name.startswith("VM."):
            continue
        if bool(getattr(item, "is_flexible", False)):
            continue
        results.append(
            {
                "name": shape_name,
                "ocpus": getattr(item, "ocpus", None),
                "memory_in_gbs": getattr(item, "memory_in_gbs", None),
                "networking_bandwidth_in_gbps": getattr(item, "networking_bandwidth_in_gbps", None),
                "is_flexible": bool(getattr(item, "is_flexible", False)),
            }
        )
    results.sort(key=lambda item: item["name"].lower())
    return results


def _sanitize_hostname_label(vm_name: str) -> str:
    label = re.sub(r"[^a-z0-9-]", "-", (vm_name or "").lower())
    label = re.sub(r"-{2,}", "-", label).strip("-")
    if not label:
        label = "vm"
    if not label[0].isalpha():
        label = f"vm-{label}"
    return label[:63].rstrip("-")


def launch_instance(
    tenancy_key: str,
    *,
    compartment_id: str,
    availability_domain: str,
    subnet_id: str,
    image_id: str,
    shape: str,
    vm_name: str,
    assign_public_ip: bool = True,
    nsg_ids: Optional[List[str]] = None,
    ssh_public_key: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    oci, _ = _require_oci_sdk()
    _, _, compute_client, _ = _client_bundle(tenancy_key)
    metadata = {}
    if ssh_public_key:
        metadata["ssh_authorized_keys"] = ssh_public_key.strip()

    vnic_details = oci.core.models.CreateVnicDetails(
        subnet_id=subnet_id,
        assign_public_ip=assign_public_ip,
        nsg_ids=[item for item in (nsg_ids or []) if item],
    )
    source_details = oci.core.models.InstanceSourceViaImageDetails(
        source_type="image",
        image_id=image_id,
    )
    launch_details = oci.core.models.LaunchInstanceDetails(
        availability_domain=availability_domain,
        compartment_id=compartment_id,
        shape=shape,
        display_name=vm_name,
        hostname_label=_sanitize_hostname_label(vm_name),
        source_details=source_details,
        create_vnic_details=vnic_details,
        metadata=metadata or None,
        freeform_tags=tags or None,
    )
    response = compute_client.launch_instance(launch_details)
    instance = response.data
    return {
        "instance_id": instance.id,
        "vm_name": instance.display_name or vm_name,
        "lifecycle_state": getattr(instance, "lifecycle_state", "") or "",
        "availability_domain": getattr(instance, "availability_domain", "") or availability_domain,
    }
