#!/usr/bin/env python3
"""
Check NER Model Processing Status

This script monitors the Elasticsearch NER model to see:
- Current processing queue
- Number of pending requests
- Processing statistics
- Model deployment status
"""

import os
import sys
import time
import argparse
from pathlib import Path
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Elasticsearch configuration
ES_HOST = os.getenv('ES_HOST', 'localhost')
ES_PORT = int(os.getenv('ES_PORT', 9200))
ES_USERNAME = os.getenv('ES_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD')
ES_SCHEME = os.getenv('ES_SCHEME', 'http')

def create_elasticsearch_client():
    """Create and return Elasticsearch client."""
    return Elasticsearch(
        [f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}"],
        basic_auth=(ES_USERNAME, ES_PASSWORD) if ES_PASSWORD else None,
        verify_certs=False
    )

def format_time(ms):
    """Format milliseconds to human readable time."""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}m"

def stop_ner_processing(es):
    """Stop the NER model deployment to halt all processing."""
    
    model_id = "elastic__distilbert-base-uncased-finetuned-conll03-english"
    
    print("=" * 60)
    print("🛑 Stopping NER Model Processing")
    print("=" * 60)
    
    try:
        # Check current deployment status
        response = es.ml.get_trained_models_stats(model_id=model_id)
        
        if not response.get('trained_model_stats'):
            print("❌ NER model not found!")
            return
        
        stats = response['trained_model_stats'][0]
        deployment = stats.get('deployment_stats', {})
        state = deployment.get('state', 'not_deployed')
        
        # Get pending requests
        nodes = deployment.get('nodes', [])
        total_pending = sum(node.get('number_of_pending_requests', 0) 
                          for node in nodes)
        
        if state != 'started':
            print(f"ℹ️  Model is not running (state: {state})")
            return
        
        if total_pending > 0:
            print(f"⚠️  Found {total_pending} pending requests in queue")
            print("These requests will be cancelled when the model stops.")
        
        # Confirm stopping
        print(f"\n⚠️  This will STOP the NER model deployment")
        print("You will need to restart it with ./inference/install_ner_model.sh")
        response = input("Are you sure? Type 'yes' to confirm: ")
        
        if response.lower() != 'yes':
            print("❌ Cancelled - model continues running")
            return
        
        print("\n🔄 Stopping model deployment...")
        
        # Stop the deployment
        result = es.ml.stop_trained_model_deployment(
            model_id=model_id,
            force=True  # Force stop even if there are pending requests
        )
        
        print("✅ Stop command sent successfully")
        
        # Wait a moment and check status
        import time
        time.sleep(2)
        
        # Verify it stopped
        try:
            response = es.ml.get_trained_models_stats(model_id=model_id)
            stats = response['trained_model_stats'][0]
            deployment = stats.get('deployment_stats', {})
            new_state = deployment.get('state', 'not_deployed')
            
            if new_state != 'started':
                print(f"✅ Model deployment stopped (state: {new_state})")
            else:
                print(f"⚠️  Model may still be stopping (state: {new_state})")
        except:
            print("✅ Model deployment stopped")
        
        print("\n✨ NER processing stopped!")
        print("To restart the model, run: ./inference/install_ner_model.sh")
        
    except Exception as e:
        print(f"❌ Error stopping model: {str(e)}")
        print("\nTry running: curl -X POST -u elastic:$ES_PASSWORD localhost:9200/_ml/trained_models/elastic__distilbert-base-uncased-finetuned-conll03-english/deployment/_stop?force=true")

def clear_ner_data(es):
    """Clear all NER-processed data from the wikipedia_ner index."""
    
    print("=" * 60)
    print("🗑️  Clearing NER Data")
    print("=" * 60)
    
    if not es.indices.exists(index='wikipedia_ner'):
        print("ℹ️  No wikipedia_ner index found - nothing to clear")
        return
    
    # Get current count
    count = es.count(index='wikipedia_ner')['count']
    print(f"📊 Found {count:,} documents in wikipedia_ner index")
    
    if count == 0:
        print("✅ Index is already empty")
        return
    
    # Confirm deletion
    print(f"\n⚠️  This will DELETE all {count:,} documents from wikipedia_ner index")
    response = input("Are you sure? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("❌ Cancelled - no data was deleted")
        return
    
    print("\n🔄 Deleting all documents...")
    
    try:
        # Delete all documents in the index
        result = es.delete_by_query(
            index='wikipedia_ner',
            body={
                "query": {
                    "match_all": {}
                }
            },
            wait_for_completion=True,
            refresh=True
        )
        
        deleted = result.get('deleted', 0)
        print(f"✅ Successfully deleted {deleted:,} documents")
        
        # Verify deletion
        new_count = es.count(index='wikipedia_ner')['count']
        if new_count == 0:
            print("✅ Index is now empty")
        else:
            print(f"⚠️  {new_count:,} documents remain in index")
            
    except Exception as e:
        print(f"❌ Error clearing data: {str(e)}")
        return
    
    print("\n✨ NER data cleared successfully!")
    print("You can now run process_wikipedia_ner.py to reprocess articles")

def check_ner_status(es, watch=False, interval=5):
    """Check and display NER model processing status."""
    
    model_id = "elastic__distilbert-base-uncased-finetuned-conll03-english"
    
    while True:
        try:
            # Get model stats
            response = es.ml.get_trained_models_stats(model_id=model_id)
            
            if not response.get('trained_model_stats'):
                print("❌ NER model not found!")
                return
            
            stats = response['trained_model_stats'][0]
            
            # Clear screen if watching
            if watch:
                os.system('clear' if os.name == 'posix' else 'cls')
            
            print("=" * 60)
            print("🤖 NER Model Status Monitor")
            print("=" * 60)
            print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Deployment status
            deployment = stats.get('deployment_stats', {})
            state = deployment.get('state', 'not_deployed')
            
            if state == 'started':
                print("✅ Model Status: DEPLOYED & RUNNING")
            else:
                print(f"⚠️  Model Status: {state.upper()}")
                
            print()
            
            # Pipeline statistics
            ingest_stats = stats.get('ingest', {}).get('total', {})
            pipeline_stats = stats.get('ingest', {}).get('pipelines', {}).get('wikipedia_ner_pipeline', {})
            
            if pipeline_stats:
                print("📊 Pipeline Statistics:")
                print(f"  Total processed: {pipeline_stats.get('count', 0):,}")
                print(f"  Currently processing: {pipeline_stats.get('current', 0)}")
                print(f"  Failed: {pipeline_stats.get('failed', 0)}")
                print(f"  Total time: {format_time(pipeline_stats.get('time_in_millis', 0))}")
                
                if pipeline_stats.get('count', 0) > 0:
                    avg_time = pipeline_stats.get('time_in_millis', 0) / pipeline_stats.get('count', 1)
                    print(f"  Avg time per doc: {format_time(avg_time)}")
                print()
            
            # Node-specific stats
            nodes = deployment.get('nodes', [])
            if nodes:
                print("🖥️  Processing Nodes:")
                for node_info in nodes:
                    node_data = list(node_info.get('node', {}).values())[0] if node_info.get('node') else {}
                    node_name = node_data.get('name', 'Unknown')
                    
                    pending = node_info.get('number_of_pending_requests', 0)
                    inference_count = node_info.get('inference_count', 0)
                    avg_time = node_info.get('average_inference_time_ms', 0)
                    throughput = node_info.get('throughput_last_minute', 0)
                    
                    print(f"\n  Node: {node_name}")
                    print(f"    🔄 Pending requests: {pending}")
                    print(f"    📈 Total inferences: {inference_count:,}")
                    print(f"    ⏱️  Avg inference time: {avg_time:.1f}ms")
                    print(f"    💨 Throughput (last min): {throughput} docs/min")
                    
                    if pending > 0:
                        print(f"    ⚠️  PROCESSING IN PROGRESS - {pending} documents queued")
                        if avg_time > 0:
                            estimated_time = (pending * avg_time) / 1000
                            print(f"    ⏳ Estimated completion: ~{format_time(estimated_time * 1000)}")
            
            # Overall inference stats
            inference_stats = stats.get('inference_stats', {})
            if inference_stats:
                print("\n📈 Overall Inference Statistics:")
                print(f"  Total inferences: {inference_stats.get('inference_count', 0):,}")
                print(f"  Failures: {inference_stats.get('failure_count', 0)}")
                print(f"  Cache misses: {inference_stats.get('cache_miss_count', 0)}")
            
            # Index statistics
            print("\n📚 Index Statistics:")
            
            # Check source Wikipedia indices for total available documents
            source_indices = ['wikipedia', 'wiki_summaries', 'wiki_chunks']
            total_available = 0
            
            for index in source_indices:
                if es.indices.exists(index=index):
                    try:
                        count = es.count(index=index)['count']
                        if count > 0:
                            total_available += count
                    except:
                        pass
            
            if total_available > 0:
                print(f"  Total Wikipedia documents available: {total_available:,}")
            
            # Check wikipedia_ner index
            if es.indices.exists(index='wikipedia_ner'):
                count = es.count(index='wikipedia_ner')['count']
                print(f"  Documents in wikipedia_ner: {count:,}")
                
                # Check for successfully processed documents
                processed_query = {
                    "query": {
                        "term": {"ner_processed": True}
                    }
                }
                processed_count = es.count(index='wikipedia_ner', body=processed_query)['count']
                print(f"  Successfully processed: {processed_count:,}")
                
                # Calculate remaining documents
                if total_available > 0:
                    remaining = total_available - processed_count
                    if remaining > 0:
                        print(f"  📋 Documents remaining to process: {remaining:,}")
                        percentage = (processed_count / total_available) * 100
                        print(f"  📊 Progress: {percentage:.1f}% complete")
                    else:
                        print(f"  ✅ All available documents processed!")
                
                # Check for errors
                error_query = {
                    "query": {
                        "exists": {"field": "ner_error"}
                    }
                }
                error_count = es.count(index='wikipedia_ner', body=error_query)['count']
                if error_count > 0:
                    print(f"  ⚠️  Documents with errors: {error_count:,}")
            
            print("\n" + "=" * 60)
            
            # Check if there's active processing
            total_pending = sum(node.get('number_of_pending_requests', 0) 
                              for node in nodes)
            
            if total_pending > 0:
                print(f"⚠️  ACTIVE PROCESSING: {total_pending} documents in queue")
                print("    The model is currently processing documents.")
                print("    This may cause timeouts for new requests.")
            else:
                print("✅ No pending requests - model is idle")
            
            if not watch:
                break
            
            print(f"\n🔄 Refreshing in {interval} seconds... (Ctrl+C to stop)")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print("\n👋 Stopped monitoring")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            if not watch:
                break
            time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(
        description='Monitor NER model processing status or clear NER data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check status once
  python check_ner_status.py
  
  # Watch status continuously (updates every 5 seconds)
  python check_ner_status.py --watch
  
  # Watch with custom interval
  python check_ner_status.py --watch --interval 10
  
  # Stop the NER model (halts all processing)
  python check_ner_status.py --stop
  
  # Clear all NER-processed data
  python check_ner_status.py --clear
        """
    )
    
    parser.add_argument(
        '--watch', '-w',
        action='store_true',
        help='Continuously monitor status'
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help='Update interval in seconds when watching (default: 5)'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear all NER-processed data from wikipedia_ner index'
    )
    
    parser.add_argument(
        '--stop',
        action='store_true',
        help='Stop the NER model deployment to halt all processing'
    )
    
    args = parser.parse_args()
    
    # Create Elasticsearch client
    es = create_elasticsearch_client()
    
    # Verify connection
    if not es.ping():
        print("❌ Cannot connect to Elasticsearch!")
        return 1
    
    # Handle actions in order of priority
    if args.stop:
        stop_ner_processing(es)
    elif args.clear:
        clear_ner_data(es)
    else:
        # Check status
        check_ner_status(es, watch=args.watch, interval=args.interval)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())