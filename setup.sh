#!/bin/bash
# Multi-Cloud Portal Quick Setup Guide
# This script provides interactive guidance for setting up the application

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${BOLD}${BLUE}===================================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}===================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Main script
clear
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║   Multi-Cloud Portal Setup Assistant              ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env exists
if [ -f ".env" ]; then
    print_success ".env file exists"
else
    print_warning ".env file not found"
    echo ""
    read -p "Would you like to create .env from template? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .env.template .env
        print_success "Created .env file from template"
        print_warning "Please edit .env file with your actual credentials"
        echo ""
        read -p "Press Enter to continue after you've edited .env..."
    else
        print_error "Cannot proceed without .env file"
        exit 1
    fi
fi

# Run configuration validation
print_header "Validating Configuration"
echo "Running configuration validator..."
echo ""

if python3 validate_config.py; then
    print_success "Configuration validation passed!"
else
    print_error "Configuration validation failed"
    print_info "Please fix the issues above and run this script again"
    exit 1
fi

# Offer setup options
print_header "Choose Your Setup Path"
echo ""
echo "You have two options for GCP access:"
echo ""
echo -e "${BOLD}Option 1: Quick Start (Recommended for Testing)${NC}"
echo "  • Works immediately without GCP configuration"
echo "  • Users login with Azure AD for Azure resources"
echo "  • Users login with Google for GCP resources (separate login)"
echo "  • Easy to set up, works right away"
echo ""
echo -e "${BOLD}Option 2: Full SSO (Recommended for Production)${NC}"
echo "  • Single sign-on across Azure and GCP"
echo "  • Requires GCP Workload Identity Federation setup"
echo "  • Users login once with Azure AD for all clouds"
echo "  • More complex initial setup"
echo ""
read -p "Which option do you want? (1 for Quick Start, 2 for Full SSO): " -n 1 -r
echo ""

if [[ $REPLY == "1" ]]; then
    print_header "Quick Start Setup"
    print_info "This setup requires:"
    echo "  1. Azure AD credentials (REQUIRED - already in .env)"
    echo "  2. Google OAuth credentials (OPTIONAL - for GCP access)"
    echo ""
    
    # Check if Google OAuth is configured
    if grep -q "^GOOGLE_CLIENT_ID=" .env 2>/dev/null && grep -q "^GOOGLE_CLIENT_SECRET=" .env 2>/dev/null; then
        print_success "Google OAuth appears to be configured"
    else
        print_warning "Google OAuth not configured"
        print_info "Users won't be able to access GCP resources"
        print_info "To enable GCP access, follow OAUTH_SETUP_GUIDE.md to get Google OAuth credentials"
    fi
    
    echo ""
    print_info "Starting application..."
    echo ""
    echo "Run: docker-compose up --build"
    echo ""
    print_success "Quick Start setup complete!"
    print_info "Access the application at: http://localhost:8000"
    
elif [[ $REPLY == "2" ]]; then
    print_header "Full SSO Setup"
    print_info "This setup requires GCP Workload Identity Federation configuration"
    echo ""
    
    # Check if GCP WIF is configured in .env
    if grep -q "^GCP_PROJECT_NUMBER=" .env 2>/dev/null && \
       grep -q "^GCP_WIF_POOL_ID=" .env 2>/dev/null && \
       grep -q "^GCP_WIF_PROVIDER_ID=" .env 2>/dev/null; then
        print_success "GCP WIF environment variables are set"
    else
        print_warning "GCP WIF environment variables not fully configured in .env"
    fi
    
    echo ""
    print_info "To complete Full SSO setup, you need to:"
    echo ""
    echo "  1. Configure GCP Workload Identity Federation (in GCP Console)"
    echo "     Follow the detailed guide in: ${BOLD}SSO_CROSS_CLOUD_SETUP.md${NC}"
    echo ""
    echo "  2. Key steps:"
    echo "     • Create Workload Identity Pool in GCP"
    echo "     • Create OIDC Provider with Azure AD settings"
    echo "     • Configure allowed audiences (use your Azure AD Client ID)"
    echo "     • Grant IAM permissions"
    echo ""
    echo "  3. Update .env with GCP WIF values:"
    echo "     • GCP_PROJECT_NUMBER"
    echo "     • GCP_WIF_POOL_ID"
    echo "     • GCP_WIF_PROVIDER_ID"
    echo "     • GCP_SERVICE_ACCOUNT_EMAIL (optional)"
    echo ""
    
    read -p "Have you already configured GCP WIF in GCP Console? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_success "Great! Starting application..."
        echo ""
        echo "Run: docker-compose up --build"
        echo ""
        print_success "Full SSO setup complete!"
        print_info "Access the application at: http://localhost:8000"
    else
        print_warning "Please complete GCP WIF configuration first"
        print_info "Detailed instructions: ${BOLD}SSO_CROSS_CLOUD_SETUP.md${NC}"
        print_info "After configuration, run this script again or start directly with:"
        echo ""
        echo "  docker-compose up --build"
    fi
else
    print_error "Invalid option. Please run the script again."
    exit 1
fi

# Final instructions
print_header "Next Steps"
echo "1. Start the application:"
echo "   ${BOLD}docker-compose up --build${NC}"
echo ""
echo "2. Access the application:"
echo "   ${BOLD}http://localhost:8000${NC}"
echo ""
echo "3. Login:"
echo "   • Use Azure AD credentials for Azure resources"
echo "   • Use Google credentials for GCP (if Quick Start)"
echo "   • Azure AD for everything (if Full SSO configured)"
echo ""
echo "4. Troubleshooting:"
echo "   • Check logs: docker-compose logs -f app"
echo "   • Validate config: python3 validate_config.py"
echo "   • See documentation: SSO_CROSS_CLOUD_SETUP.md"
echo ""
print_success "Setup assistant complete!"
echo ""
