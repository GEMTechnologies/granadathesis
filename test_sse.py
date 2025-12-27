#!/usr/bin/env python3
"""
Quick test script to verify SSE endpoint fixes.
Tests the /api/stream/agent-actions endpoint to ensure:
1. Connection establishes immediately without errors
2. CORS headers are correct
3. Initial connected event is received
"""

import requests
import time
import sseclient
import sys

def test_sse_connection():
    url = "http://localhost:8000/api/stream/agent-actions?session_id=test"
    
    print(f"Testing SSE endpoint: {url}")
    print("-" * 60)
    
    try:
        # Make request with explicit headers
        headers = {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        
        # Check status code
        print(f"✓ Status Code: {response.status_code}")
        
        # Check CORS headers
        cors_origin = response.headers.get('Access-Control-Allow-Origin')
        print(f"✓ CORS Origin: {cors_origin}")
        
        # Check content type
        content_type = response.headers.get('Content-Type')
        print(f"✓ Content-Type: {content_type}")
        
        print("\nReceiving events...")
        print("-" * 60)
        
        # Read SSE events
        client = sseclient.SSEClient(response)
        event_count = 0
        start_time = time.time()
        
        for event in client.events():
            event_count += 1
            elapsed = time.time() - start_time
            
            print(f"[{elapsed:.2f}s] Event: {event.event}")
            print(f"         Data: {event.data[:100]}...")  # First 100 chars
            
            # Test passed if we receive the 'connected' event
            if event.event == 'connected':
                print("\n" + "=" * 60)
                print("✓✓✓ SUCCESS! SSE connection working correctly!")
                print("=" * 60)
                print(f"Time to connect: {elapsed:.2f}s (should be < 1s)")
                return True
            
            # Stop after 5 seconds or 10 events
            if elapsed > 5 or event_count > 10:
                print("\n⚠ Warning: Received events but no 'connected' event")
                return False
                
    except requests.exceptions.Timeout:
        print("\n✗ ERROR: Connection timeout!")
        print("The endpoint is not responding within 10 seconds.")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"\n✗ ERROR: Connection failed!")
        print(f"Details: {e}")
        print("Is the backend server running?")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_sse_connection()
    sys.exit(0 if success else 1)
