#!/bin/bash
# Scout Release Verification Wrapper
# This script provides a simple way to run the release verification process

# Determine script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
VERSION="1.0.0"
OUTPUT_DIR="$PROJECT_ROOT/verification_results"
SKIP_BUILD=0
SKIP_TESTS=0
SKIP_DOCS=0
SKIP_CHECK=0

# Text colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Display help
function show_help() {
    echo -e "${BLUE}Scout Release Verification Tool${NC}"
    echo
    echo "This script helps verify that the Scout application is ready for release."
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -v, --version VERSION    Version to verify (default: 1.0.0)"
    echo "  -o, --output-dir DIR     Directory to store verification results"
    echo "  -b, --skip-build         Skip building executables"
    echo "  -t, --skip-tests         Skip running tests"
    echo "  -d, --skip-docs          Skip documentation checks"
    echo "  -c, --skip-check         Skip version checks"
    echo "  -a, --skip-all           Skip all checks and only generate reports"
    echo "  -h, --help               Show this help message"
    echo
    echo "Example:"
    echo "  $0 --version 1.0.0 --skip-tests"
    echo
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -b|--skip-build)
            SKIP_BUILD=1
            shift
            ;;
        -t|--skip-tests)
            SKIP_TESTS=1
            shift
            ;;
        -d|--skip-docs)
            SKIP_DOCS=1
            shift
            ;;
        -c|--skip-check)
            SKIP_CHECK=1
            shift
            ;;
        -a|--skip-all)
            SKIP_BUILD=1
            SKIP_TESTS=1
            SKIP_DOCS=1
            SKIP_CHECK=1
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Header
echo -e "\n${PURPLE}=========================================================${NC}"
echo -e "${PURPLE}Scout $VERSION Release Verification${NC}"
echo -e "${PURPLE}=========================================================${NC}\n"

# Check if Python is installed
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python is not installed or not in PATH${NC}"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

# Determine Python command
PYTHON_CMD="python"
if ! command -v python &> /dev/null && command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version | cut -d " " -f 2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d "." -f 1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d "." -f 2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${YELLOW}Warning: Python 3.9 or higher is recommended (detected $PYTHON_VERSION)${NC}"
fi

# Build command
CMD="$PYTHON_CMD $SCRIPT_DIR/run_release_verification.py --version $VERSION --output-dir $OUTPUT_DIR"

if [ $SKIP_BUILD -eq 1 ]; then
    CMD="$CMD --skip-build"
    echo -e "${YELLOW}Skipping build process${NC}"
fi

if [ $SKIP_TESTS -eq 1 ]; then
    CMD="$CMD --skip-tests"
    echo -e "${YELLOW}Skipping tests${NC}"
fi

if [ $SKIP_DOCS -eq 1 ]; then
    CMD="$CMD --skip-docs"
    echo -e "${YELLOW}Skipping documentation checks${NC}"
fi

if [ $SKIP_CHECK -eq 1 ]; then
    CMD="$CMD --skip-check"
    echo -e "${YELLOW}Skipping version checks${NC}"
fi

# Print command
echo -e "${BLUE}Running command:${NC} $CMD"
echo

# Run verification
eval $CMD
RESULT=$?

# Print exit status
if [ $RESULT -eq 0 ]; then
    echo -e "\n${GREEN}Verification completed successfully!${NC}"
else
    echo -e "\n${RED}Verification completed with errors. Please check the report for details.${NC}"
fi

echo
echo -e "${BLUE}Next steps:${NC}"
echo "1. Review the verification report in the output directory"
echo "2. Complete any remaining items in the verification checklist"
echo "3. Address any failed tests or checks"
echo "4. Sign off on the release when all checks pass"
echo

exit $RESULT 