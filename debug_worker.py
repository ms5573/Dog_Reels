#!/usr/bin/env python3

import redis
import json
import os

def test_redis_connection():
    """Test Redis connection and queue operations"""
    try:
        # Connect to Redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        print(f"Connecting to Redis at: {redis_url}")
        
        # For local Redis, use simple connection
        if redis_url.startswith('redis://localhost') or redis_url.startswith('redis://127.0.0.1'):
            r = redis.Redis(host='localhost', port=6379, db=0)
        else:
            r = redis.from_url(redis_url)
        
        # Test connection
        print("Testing Redis connection...")
        result = r.ping()
        print(f"Redis ping result: {result}")
        
        # Check queue contents
        task_queue = 'pet_video_tasks'
        result_queue = 'pet_video_results'
        
        print(f"\nQueue status:")
        print(f"Task queue '{task_queue}' length: {r.llen(task_queue)}")
        print(f"Result queue '{result_queue}' length: {r.llen(result_queue)}")
        
        # Show tasks in queue
        tasks = r.lrange(task_queue, 0, -1)
        print(f"\nTasks in queue:")
        for i, task in enumerate(tasks):
            try:
                task_data = json.loads(task.decode())
                print(f"  Task {i+1}: {task_data}")
            except Exception as e:
                print(f"  Task {i+1}: Error parsing - {e}")
        
        # Test blocking pop (with short timeout)
        print(f"\nTesting blocking pop from '{task_queue}' (5 second timeout)...")
        result = r.blpop(task_queue, timeout=5)
        if result:
            queue_name, task_data = result
            print(f"Got task from queue: {task_data.decode()}")
            # Put it back
            r.lpush(task_queue, task_data)
            print("Task put back in queue")
        else:
            print("No task received (timeout)")
            
    except Exception as e:
        print(f"Error testing Redis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_redis_connection() 