#!/bin/bash
"""
Filter Docker Compose logs by Lead ID
Usage: ./filter_logs.sh <lead_id> [lines]

Examples:
  ./filter_logs.sh 6KPmcTnNXKnw9QlYO1BNCg       # Show all logs for this lead
  ./filter_logs.sh 6KPmcTnNXKnw9QlYO1BNCg 50    # Show last 50 matching lines
"""

LEAD_ID="$1"
LINES="${2:-100}"  # Default to 100 lines if not specified

if [ -z "$LEAD_ID" ]; then
    echo "❌ Error: Lead ID is required"
    echo "Usage: $0 <lead_id> [lines]" 
    echo "Example: $0 6KPmcTnNXKnw9QlYO1BNCg 50"
    exit 1
fi

echo "🔍 Filtering Docker logs for Lead ID: $LEAD_ID"
echo "📊 Showing last $LINES matching entries"
echo "=============================================="

# Change to the correct directory
cd /var/www/yelp/backend 2>/dev/null || cd "$(dirname "$0")/.." || {
    echo "❌ Error: Could not find Docker Compose directory"
    exit 1
}

# Run docker-compose logs and filter by Lead ID
docker-compose logs --no-color 2>/dev/null | grep -a "$LEAD_ID" | tail -n "$LINES" | while IFS= read -r line; do
    # Add color coding for different log levels
    if echo "$line" | grep -q "ERROR"; then
        echo -e "\033[31m$line\033[0m"  # Red for errors
    elif echo "$line" | grep -q "WARNING\|WARN"; then
        echo -e "\033[33m$line\033[0m"  # Yellow for warnings  
    elif echo "$line" | grep -q "🛑\|CANCEL"; then
        echo -e "\033[1;31m$line\033[0m"  # Bold red for cancellations
    elif echo "$line" | grep -q "🤖\|AUTOMATED"; then
        echo -e "\033[32m$line\033[0m"  # Green for automated messages
    elif echo "$line" | grep -q "👨‍💼\|MANUAL"; then
        echo -e "\033[1;33m$line\033[0m"  # Bold yellow for manual messages
    else
        echo "$line"  # Default color
    fi
done

# Show summary
TOTAL_LINES=$(docker-compose logs --no-color 2>/dev/null | grep -c "$LEAD_ID")
echo ""
echo "📈 Summary:"
echo "  Total log entries for $LEAD_ID: $TOTAL_LINES"
echo "  Displayed: $LINES (last entries)"

if [ "$TOTAL_LINES" -gt "$LINES" ]; then
    echo "  ℹ️  Use './filter_logs.sh $LEAD_ID $TOTAL_LINES' to see all entries"
fi
