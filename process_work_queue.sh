#!/bin/bash
# Automated Work Queue Processor
# Safely processes /tmp/torch_work_queue.txt without API hammering

QUEUE_FILE="/tmp/torch_work_queue.txt"
PROCESSED_FILE="/tmp/torch_processed_queue.txt"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)

# Check if queue file exists
if [ ! -f "$QUEUE_FILE" ]; then
    echo "📭 No work queue file found" >&2
    exit 0
fi

# Check if queue is empty
if [ ! -s "$QUEUE_FILE" ]; then
    echo "📪 Work queue is empty" >&2
    exit 0
fi

echo "🔄 Processing work queue at $TIMESTAMP" >&2

# Process queue line by line
while IFS= read -r line; do
    if [ -n "$line" ]; then
        echo "📋 Processing: $line" >&2
        
        # Parse work type
        if [[ "$line" == WORK_FOUND:* ]]; then
            work_data="${line#WORK_FOUND: }"
            echo "⚡ Work item: $work_data" >&2
            
            # Add to Redis work stream for tracking
            redis-cli -p 18000 XADD "nova.processed.work" '*' \
                type "work" \
                content "$work_data" \
                processed_at "$TIMESTAMP" \
                processor "automated_queue" >/dev/null
                
        elif [[ "$line" == TODO_FOUND:* ]]; then
            todo_data="${line#TODO_FOUND: }"
            echo "📝 TODO item: $todo_data" >&2
            
            # Add to processed todos stream
            redis-cli -p 18000 XADD "nova.processed.todos" '*' \
                type "todo" \
                content "$todo_data" \
                processed_at "$TIMESTAMP" \
                processor "automated_queue" >/dev/null
                
        elif [[ "$line" == COORD_MSG:* ]]; then
            coord_data="${line#COORD_MSG: }"
            echo "💬 Coordination: $coord_data" >&2
            
            # Add to coordination tracking
            redis-cli -p 18000 XADD "nova.processed.coordination" '*' \
                type "coordination" \
                content "$coord_data" \
                processed_at "$TIMESTAMP" \
                processor "automated_queue" >/dev/null
                
        elif [[ "$line" == SELF_GENERATED:* ]]; then
            gen_data="${line#SELF_GENERATED: }"
            echo "🏭 Self-generated: $gen_data" >&2
            
            # Track self-generation patterns
            redis-cli -p 18000 XADD "nova.processed.generated" '*' \
                type "self_generated" \
                content "$gen_data" \
                processed_at "$TIMESTAMP" \
                processor "automated_queue" >/dev/null
        fi
        
        # Move processed item to archive
        echo "$TIMESTAMP - $line" >> "$PROCESSED_FILE"
        
        # Small delay to prevent overwhelming
        sleep 0.1
    fi
done < "$QUEUE_FILE"

# Archive the original queue
if [ -s "$QUEUE_FILE" ]; then
    mv "$QUEUE_FILE" "${QUEUE_FILE}.processed.${TIMESTAMP}"
    echo "✅ Archived queue as ${QUEUE_FILE}.processed.${TIMESTAMP}" >&2
fi

# Create new empty queue
touch "$QUEUE_FILE"

# Log processing completion
redis-cli -p 18000 XADD "torch.continuous.ops" '*' \
    timestamp "$TIMESTAMP" \
    status "QUEUE_PROCESSED" \
    processor "automated_queue" \
    action "work_queue_batch_complete" >/dev/null

echo "🎉 Work queue processing complete!" >&2