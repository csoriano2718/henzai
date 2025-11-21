#!/usr/bin/env bash
#
# Run all henzai tests locally
#
# Usage:
#   ./run-tests.sh              # Run all tests
#   ./run-tests.sh unit         # Run only unit tests
#   ./run-tests.sh integration  # Run only integration tests
#   ./run-tests.sh rag          # Run only RAG tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Log functions
log_info() {
    echo -e "ℹ️  $1"
}

log_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

log_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Run a test and track result
run_test() {
    local test_file="$1"
    local test_name="$(basename "$test_file" .py)"
    
    log_info "Running $test_name..."
    
    if python3 "$test_file"; then
        log_pass "$test_name"
        return 0
    else
        log_fail "$test_name"
        return 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check henzai-daemon
    if ! systemctl --user is-active henzai-daemon > /dev/null 2>&1; then
        log_warn "henzai-daemon is not running"
        log_info "Starting henzai-daemon..."
        systemctl --user start henzai-daemon
        sleep 3
    fi
    
    # Check ramalama
    if ! systemctl --user is-active ramalama > /dev/null 2>&1; then
        log_warn "ramalama service is not running"
        log_info "Starting ramalama..."
        systemctl --user start ramalama
        sleep 5
    fi
    
    log_pass "Prerequisites OK"
}

# Run unit tests
run_unit_tests() {
    echo ""
    echo "======================================"
    echo "Unit Tests"
    echo "======================================"
    
    cd "$PROJECT_ROOT/henzai-daemon"
    
    if [ -d "tests" ]; then
        log_info "Running daemon unit tests..."
        if python3 -m pytest tests/ -v; then
            log_pass "Daemon unit tests"
        else
            log_fail "Daemon unit tests"
        fi
    fi
    
    cd "$PROJECT_ROOT"
}

# Run integration tests
run_integration_tests() {
    echo ""
    echo "======================================"
    echo "Integration Tests"
    echo "======================================"
    
    cd "$PROJECT_ROOT"
    
    local tests=(
        "tests/test-streaming.py"
        "tests/test-reasoning.py"
        "tests/test-thinking-chunks.py"
        "tests/test-model-switch.py"
        "tests/test-history.py"
        "tests/test-newchat.py"
        "tests/test-health-check.py"
    )
    
    for test in "${tests[@]}"; do
        if [ -f "$test" ]; then
            run_test "$test"
        else
            log_warn "Test not found: $test"
        fi
    done
}

# Run RAG tests
run_rag_tests() {
    echo ""
    echo "======================================"
    echo "RAG Tests"
    echo "======================================"
    
    cd "$PROJECT_ROOT"
    
    # Check if RAG is available
    if ! podman images | grep -q "ramalama/cuda-rag"; then
        log_warn "RAG container not found"
        log_info "Pulling RAG container (this may take a few minutes)..."
        podman pull quay.io/ramalama/cuda-rag:latest || {
            log_fail "Failed to pull RAG container"
            return 1
        }
    fi
    
    local tests=(
        "tests/test-rag-e2e.py"
        "tests/test-rag-reasoning.py"
    )
    
    for test in "${tests[@]}"; do
        if [ -f "$test" ]; then
            run_test "$test"
        else
            log_warn "Test not found: $test"
        fi
    done
}

# Print summary
print_summary() {
    echo ""
    echo "======================================"
    echo "Test Summary"
    echo "======================================"
    echo -e "Total:  $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    else
        echo -e "Failed: $FAILED_TESTS"
    fi
    echo "======================================"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ Some tests failed${NC}"
        return 1
    fi
}

# Main
main() {
    local test_type="${1:-all}"
    
    echo "======================================"
    echo "henzai Test Suite"
    echo "======================================"
    
    check_prerequisites
    
    case "$test_type" in
        unit)
            run_unit_tests
            ;;
        integration)
            run_integration_tests
            ;;
        rag)
            run_rag_tests
            ;;
        all)
            run_unit_tests
            run_integration_tests
            run_rag_tests
            ;;
        *)
            echo "Unknown test type: $test_type"
            echo "Usage: $0 [unit|integration|rag|all]"
            exit 1
            ;;
    esac
    
    print_summary
}

main "$@"

