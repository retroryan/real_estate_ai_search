#!/usr/bin/env python3
"""
Comprehensive ML Status Check Script
Checks the status of both NER and Embedding models, pipelines, and indices
"""

import os
import json
from pathlib import Path
from datetime import datetime
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from tabulate import tabulate
from typing import Dict, List, Any

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Elasticsearch configuration
ES_HOST = os.getenv('ES_HOST', 'localhost')
ES_PORT = int(os.getenv('ES_PORT', 9200))
ES_USERNAME = os.getenv('ES_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD')
ES_SCHEME = os.getenv('ES_SCHEME', 'http')

# Model IDs
NER_MODEL_ID = "elastic__distilbert-base-uncased-finetuned-conll03-english"
EMBEDDING_MODEL_ID = "sentence-transformers__all-minilm-l6-v2"

class MLStatusChecker:
    def __init__(self, es_client):
        self.es = es_client
        self.status = {
            'models': {},
            'pipelines': {},
            'indices': {},
            'summary': {}
        }
    
    def check_elasticsearch_connection(self) -> bool:
        """Check if Elasticsearch is accessible."""
        try:
            info = self.es.info()
            self.status['elasticsearch'] = {
                'connected': True,
                'cluster_name': info['cluster_name'],
                'version': info['version']['number']
            }
            return True
        except Exception as e:
            self.status['elasticsearch'] = {
                'connected': False,
                'error': str(e)
            }
            return False
    
    def check_model_status(self, model_id: str, model_type: str) -> Dict:
        """Check the status of a specific model."""
        try:
            response = self.es.ml.get_trained_models_stats(model_id=model_id)
            
            if response['trained_model_stats']:
                stats = response['trained_model_stats'][0]
                model_info = {
                    'exists': True,
                    'type': model_type,
                    'model_id': stats['model_id'],
                    'model_size_mb': stats['model_size_stats']['model_size_bytes'] / 1024 / 1024,
                    'pipeline_count': stats.get('pipeline_count', 0)
                }
                
                # Check deployment status
                deployment = stats.get('deployment_stats', {})
                if deployment:
                    model_info['deployment'] = {
                        'state': deployment.get('state', 'not_deployed'),
                        'allocation_status': deployment.get('allocation_status', {}).get('state', 'unknown'),
                        'inference_count': stats.get('inference_stats', {}).get('inference_count', 0),
                        'cache_size': deployment.get('cache_size', 'N/A'),
                        'threads': deployment.get('threads_per_allocation', 1),
                        'allocations': deployment.get('number_of_allocations', 0)
                    }
                    
                    # Get start time if available
                    if deployment.get('start_time'):
                        start_time = deployment['start_time']
                        model_info['deployment']['uptime'] = self._format_uptime(start_time)
                else:
                    model_info['deployment'] = {
                        'state': 'not_deployed',
                        'allocation_status': 'none',
                        'inference_count': 0
                    }
                
                return model_info
            else:
                return {'exists': False, 'type': model_type}
                
        except Exception as e:
            return {
                'exists': False,
                'type': model_type,
                'error': str(e)[:100]
            }
    
    def check_pipeline_status(self, pipeline_name: str, pipeline_type: str) -> Dict:
        """Check if a pipeline exists and its configuration."""
        try:
            response = self.es.ingest.get_pipeline(id=pipeline_name)
            
            if pipeline_name in response:
                pipeline = response[pipeline_name]
                processors = pipeline.get('processors', [])
                
                # Count processor types
                processor_types = {}
                for proc in processors:
                    for proc_type in proc.keys():
                        processor_types[proc_type] = processor_types.get(proc_type, 0) + 1
                
                return {
                    'exists': True,
                    'type': pipeline_type,
                    'description': pipeline.get('description', 'No description'),
                    'processor_count': len(processors),
                    'processor_types': processor_types,
                    'has_inference': 'inference' in processor_types
                }
            else:
                return {'exists': False, 'type': pipeline_type}
                
        except Exception as e:
            return {
                'exists': False,
                'type': pipeline_type,
                'error': str(e)[:100]
            }
    
    def check_index_status(self, index_name: str, index_type: str) -> Dict:
        """Check if an index exists and get its statistics."""
        try:
            if not self.es.indices.exists(index=index_name):
                return {'exists': False, 'type': index_type}
            
            # Get index stats
            stats = self.es.indices.stats(index=index_name)
            index_stats = stats['indices'][index_name]
            
            # Get document count
            count = self.es.count(index=index_name)['count']
            
            # Get mapping to check for special fields
            mapping = self.es.indices.get_mapping(index=index_name)
            properties = mapping[index_name]['mappings'].get('properties', {})
            
            # Check for specific field types
            has_vectors = any(
                prop.get('type') == 'dense_vector' 
                for prop in properties.values()
            )
            has_ner_fields = any(
                'ner_' in field_name 
                for field_name in properties.keys()
            )
            
            index_info = {
                'exists': True,
                'type': index_type,
                'document_count': count,
                'size_mb': index_stats['total']['store']['size_in_bytes'] / 1024 / 1024,
                'has_vectors': has_vectors,
                'has_ner_fields': has_ner_fields
            }
            
            # Get sample of processed documents if relevant
            if index_type == 'NER':
                processed = self.es.count(
                    index=index_name,
                    body={"query": {"term": {"ner_processed": True}}}
                )
                index_info['ner_processed_count'] = processed['count']
                index_info['ner_processed_percentage'] = (processed['count'] / count * 100) if count > 0 else 0
                
            elif index_type == 'Embeddings':
                processed = self.es.count(
                    index=index_name,
                    body={"query": {"term": {"embeddings_processed": True}}}
                )
                index_info['embeddings_processed_count'] = processed['count']
                index_info['embeddings_processed_percentage'] = (processed['count'] / count * 100) if count > 0 else 0
                index_info['total_vectors'] = processed['count'] * 3  # 3 embeddings per doc
            
            return index_info
            
        except Exception as e:
            return {
                'exists': False,
                'type': index_type,
                'error': str(e)[:100]
            }
    
    def _format_uptime(self, start_time: int) -> str:
        """Format uptime from milliseconds timestamp."""
        try:
            start = datetime.fromtimestamp(start_time / 1000)
            uptime = datetime.now() - start
            
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "N/A"
    
    def check_all_components(self):
        """Check all ML components."""
        # Check models
        self.status['models']['ner'] = self.check_model_status(NER_MODEL_ID, 'NER')
        self.status['models']['embedding'] = self.check_model_status(EMBEDDING_MODEL_ID, 'Text Embedding')
        
        # Check pipelines
        self.status['pipelines']['ner'] = self.check_pipeline_status('wikipedia_ner_pipeline', 'NER')
        self.status['pipelines']['embedding'] = self.check_pipeline_status('wikipedia_embedding_pipeline', 'Embedding')
        
        # Check indices
        self.status['indices']['ner'] = self.check_index_status('wikipedia_ner', 'NER')
        self.status['indices']['embeddings'] = self.check_index_status('wikipedia_embeddings', 'Embeddings')
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate overall summary statistics."""
        summary = {
            'total_models': 2,
            'models_installed': sum(1 for m in self.status['models'].values() if m.get('exists')),
            'models_deployed': sum(1 for m in self.status['models'].values() 
                                 if m.get('deployment', {}).get('state') == 'started'),
            'total_pipelines': 2,
            'pipelines_created': sum(1 for p in self.status['pipelines'].values() if p.get('exists')),
            'total_indices': 2,
            'indices_created': sum(1 for i in self.status['indices'].values() if i.get('exists')),
            'total_documents': sum(i.get('document_count', 0) for i in self.status['indices'].values() if i.get('exists')),
            'total_inferences': sum(m.get('deployment', {}).get('inference_count', 0) 
                                  for m in self.status['models'].values() if m.get('exists'))
        }
        
        # Calculate readiness
        ner_ready = (
            self.status['models']['ner'].get('exists') and
            self.status['models']['ner'].get('deployment', {}).get('state') == 'started' and
            self.status['pipelines']['ner'].get('exists') and
            self.status['indices']['ner'].get('exists')
        )
        
        embedding_ready = (
            self.status['models']['embedding'].get('exists') and
            self.status['models']['embedding'].get('deployment', {}).get('state') == 'started' and
            self.status['pipelines']['embedding'].get('exists') and
            self.status['indices']['embeddings'].get('exists')
        )
        
        summary['ner_ready'] = ner_ready
        summary['embedding_ready'] = embedding_ready
        summary['fully_operational'] = ner_ready and embedding_ready
        
        self.status['summary'] = summary
    
    def display_status(self):
        """Display comprehensive status report."""
        print("\n" + "=" * 80)
        print("🔬 ELASTICSEARCH ML STATUS REPORT")
        print("=" * 80)
        
        # Elasticsearch Connection
        print("\n📡 Elasticsearch Connection:")
        if self.status['elasticsearch']['connected']:
            print(f"  ✅ Connected to cluster: {self.status['elasticsearch']['cluster_name']}")
            print(f"  Version: {self.status['elasticsearch']['version']}")
        else:
            print(f"  ❌ Connection failed: {self.status['elasticsearch'].get('error', 'Unknown error')}")
            return
        
        # Models Status
        print("\n🤖 ML Models:")
        print("-" * 60)
        
        for model_type, model in self.status['models'].items():
            icon = "🏷️" if model_type == 'ner' else "📊"
            print(f"\n{icon} {model['type']} Model:")
            
            if model.get('exists'):
                print(f"  ✅ Installed: {model['model_id']}")
                print(f"  Size: {model['model_size_mb']:.1f} MB")
                
                deployment = model.get('deployment', {})
                state = deployment.get('state', 'not_deployed')
                
                if state == 'started':
                    print(f"  🟢 Deployed and running")
                    print(f"  Allocations: {deployment.get('allocations', 0)}")
                    print(f"  Inference count: {deployment.get('inference_count', 0):,}")
                    print(f"  Uptime: {deployment.get('uptime', 'N/A')}")
                elif state == 'starting':
                    print(f"  🟡 Starting...")
                else:
                    print(f"  🔴 Not deployed")
                
                if model.get('pipeline_count', 0) > 0:
                    print(f"  📋 Used by {model['pipeline_count']} pipeline(s)")
            else:
                print(f"  ❌ Not installed")
                if model.get('error'):
                    print(f"  Error: {model['error']}")
        
        # Pipelines Status
        print("\n🔧 Ingest Pipelines:")
        print("-" * 60)
        
        for pipeline_type, pipeline in self.status['pipelines'].items():
            icon = "🏷️" if pipeline_type == 'ner' else "📊"
            print(f"\n{icon} {pipeline['type']} Pipeline:")
            
            if pipeline.get('exists'):
                print(f"  ✅ Created")
                print(f"  Description: {pipeline['description'][:50]}...")
                print(f"  Processors: {pipeline['processor_count']}")
                
                if pipeline.get('processor_types'):
                    types = ', '.join(f"{k}({v})" for k, v in pipeline['processor_types'].items())
                    print(f"  Types: {types}")
                
                if pipeline.get('has_inference'):
                    print(f"  🧠 Has ML inference processor")
            else:
                print(f"  ❌ Not created")
        
        # Indices Status
        print("\n📚 Indices:")
        print("-" * 60)
        
        for index_type, index in self.status['indices'].items():
            icon = "🏷️" if index_type == 'ner' else "📊"
            print(f"\n{icon} {index['type']} Index:")
            
            if index.get('exists'):
                print(f"  ✅ Created")
                print(f"  Documents: {index['document_count']:,}")
                print(f"  Size: {index['size_mb']:.1f} MB")
                
                if index.get('has_vectors'):
                    print(f"  🔢 Has dense vectors")
                
                if index.get('has_ner_fields'):
                    print(f"  🏷️ Has NER entity fields")
                
                if 'ner_processed_count' in index:
                    print(f"  NER processed: {index['ner_processed_count']:,} ({index['ner_processed_percentage']:.1f}%)")
                
                if 'embeddings_processed_count' in index:
                    print(f"  Embeddings processed: {index['embeddings_processed_count']:,} ({index['embeddings_processed_percentage']:.1f}%)")
                    print(f"  Total vectors: {index['total_vectors']:,}")
            else:
                print(f"  ❌ Not created")
        
        # Summary Statistics
        print("\n📊 Summary:")
        print("-" * 60)
        
        summary = self.status['summary']
        
        # Create summary table
        summary_data = [
            ["Models", f"{summary['models_installed']}/{summary['total_models']}", 
             f"{summary['models_deployed']} deployed"],
            ["Pipelines", f"{summary['pipelines_created']}/{summary['total_pipelines']}", 
             "✓" if summary['pipelines_created'] == summary['total_pipelines'] else "⚠️"],
            ["Indices", f"{summary['indices_created']}/{summary['total_indices']}", 
             f"{summary['total_documents']:,} docs"],
            ["Total Inferences", f"{summary['total_inferences']:,}", ""]
        ]
        
        print(tabulate(summary_data, headers=["Component", "Status", "Details"], tablefmt="grid"))
        
        # System Readiness
        print("\n🚦 System Readiness:")
        print("-" * 60)
        
        if summary['ner_ready']:
            print("  ✅ NER System: Ready")
        else:
            print("  ❌ NER System: Not ready")
            self._show_ner_requirements()
        
        if summary['embedding_ready']:
            print("  ✅ Embedding System: Ready")
        else:
            print("  ❌ Embedding System: Not ready")
            self._show_embedding_requirements()
        
        print()
        if summary['fully_operational']:
            print("  🎉 All ML systems are fully operational!")
        else:
            print("  ⚠️ Some ML systems need setup or deployment")
        
        # Recommendations
        self.show_recommendations()
    
    def _show_ner_requirements(self):
        """Show what's needed for NER to be ready."""
        requirements = []
        
        if not self.status['models']['ner'].get('exists'):
            requirements.append("Install NER model: ./inference/install_ner_model.sh")
        elif self.status['models']['ner'].get('deployment', {}).get('state') != 'started':
            requirements.append("Deploy NER model (may need to stop other models first)")
        
        if not self.status['pipelines']['ner'].get('exists'):
            requirements.append("Create pipeline: python inference/setup_ner_pipeline.py")
        
        if not self.status['indices']['ner'].get('exists'):
            requirements.append("Create index: python inference/setup_ner_pipeline.py")
        
        if requirements:
            print("    Required actions:")
            for req in requirements:
                print(f"      • {req}")
    
    def _show_embedding_requirements(self):
        """Show what's needed for embeddings to be ready."""
        requirements = []
        
        if not self.status['models']['embedding'].get('exists'):
            requirements.append("Install embedding model: ./inference/install_embedding_model.sh")
        elif self.status['models']['embedding'].get('deployment', {}).get('state') != 'started':
            requirements.append("Deploy embedding model (may need to stop other models first)")
        
        if not self.status['pipelines']['embedding'].get('exists'):
            requirements.append("Create pipeline: python inference/setup_embedding_pipeline.py")
        
        if not self.status['indices']['embeddings'].get('exists'):
            requirements.append("Create index: python inference/setup_embedding_pipeline.py")
        
        if requirements:
            print("    Required actions:")
            for req in requirements:
                print(f"      • {req}")
    
    def show_recommendations(self):
        """Show recommendations based on current status."""
        print("\n💡 Recommendations:")
        print("-" * 60)
        
        recommendations = []
        
        # Check if both models are trying to run
        ner_deployed = self.status['models']['ner'].get('deployment', {}).get('state') == 'started'
        emb_deployed = self.status['models']['embedding'].get('deployment', {}).get('state') == 'started'
        
        if ner_deployed and emb_deployed:
            recommendations.append("⚠️ Both models are deployed - this may use significant resources")
            recommendations.append("   Consider deploying only one at a time based on your needs")
        
        # Check for unprocessed documents
        for index_type, index in self.status['indices'].items():
            if index.get('exists'):
                if index.get('document_count', 0) > 0:
                    if index.get('ner_processed_percentage', 100) < 100:
                        recommendations.append(f"📋 Process remaining NER documents: python inference/process_wikipedia_ner.py")
                    if index.get('embeddings_processed_percentage', 100) < 100:
                        recommendations.append(f"📊 Generate remaining embeddings: python inference/process_wikipedia_embeddings.py")
        
        # Check for low inference counts
        total_inferences = self.status['summary']['total_inferences']
        if total_inferences < 10:
            if ner_deployed:
                recommendations.append("🔍 Test NER search: python inference/search_ner.py")
            if emb_deployed:
                recommendations.append("🔍 Test semantic search: python inference/search_embeddings.py")
        
        if not recommendations:
            recommendations.append("✨ Everything looks good! Systems are ready for use.")
        
        for rec in recommendations:
            print(f"  {rec}")
    
    def export_status(self, filename: str = "ml_status.json"):
        """Export status to JSON file."""
        output_path = Path(filename)
        
        # Convert to JSON-serializable format
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'status': self.status
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"\n📁 Status exported to: {output_path}")

def create_elasticsearch_client():
    """Create and return Elasticsearch client."""
    client = Elasticsearch(
        [f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}"],
        basic_auth=(ES_USERNAME, ES_PASSWORD),
        verify_certs=False
    )
    return client

def switch_model(es, target_model: str) -> bool:
    """Switch between NER and embedding models."""
    print(f"\n🔄 Switching to {target_model.upper()} model...")
    print("-" * 60)
    
    if target_model == 'ner':
        start_model = NER_MODEL_ID
        stop_model = EMBEDDING_MODEL_ID
        start_name = "NER"
        stop_name = "Embedding"
    elif target_model in ['embed', 'embedding']:
        start_model = EMBEDDING_MODEL_ID
        stop_model = NER_MODEL_ID
        start_name = "Embedding"
        stop_name = "NER"
    else:
        print(f"❌ Invalid model: {target_model}")
        print("   Use 'ner' or 'embed'")
        return False
    
    # Check current deployment status
    try:
        # Check if target model is already running
        start_stats = es.ml.get_trained_models_stats(model_id=start_model)
        if start_stats['trained_model_stats']:
            deployment = start_stats['trained_model_stats'][0].get('deployment_stats', {})
            if deployment.get('state') == 'started':
                print(f"✅ {start_name} model is already deployed and running")
                return True
        
        # Check if we need to stop the other model
        stop_stats = es.ml.get_trained_models_stats(model_id=stop_model)
        if stop_stats['trained_model_stats']:
            deployment = stop_stats['trained_model_stats'][0].get('deployment_stats', {})
            if deployment.get('state') in ['started', 'starting']:
                print(f"⏸️  Stopping {stop_name} model to free resources...")
                
                # Force stop the model
                try:
                    es.ml.stop_trained_model_deployment(
                        model_id=stop_model,
                        force=True
                    )
                    print(f"✅ {stop_name} model stopped")
                    
                    # Wait a moment for resources to be freed
                    import time
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"⚠️  Error stopping {stop_name} model: {str(e)[:100]}")
        
        # Start the target model
        print(f"🚀 Starting {start_name} model...")
        try:
            result = es.ml.start_trained_model_deployment(
                model_id=start_model,
                wait_for='started',
                timeout='30s'
            )
            
            # Check if deployment was successful
            if result.get('assignment', {}).get('assignment_state') == 'started':
                print(f"✅ {start_name} model deployed successfully!")
                
                # Show deployment info
                allocation = result.get('assignment', {}).get('task_parameters', {})
                print(f"   Allocations: {allocation.get('number_of_allocations', 1)}")
                print(f"   Threads: {allocation.get('threads_per_allocation', 1)}")
                print(f"   Cache size: {allocation.get('cache_size', 'default')}")
                
                return True
            else:
                print(f"⚠️  Model deployment state: {result.get('assignment', {}).get('assignment_state', 'unknown')}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            if 'insufficient capacity' in error_msg.lower():
                print(f"❌ Cannot start {start_name} model: Insufficient resources")
                print("   The node doesn't have enough allocated processors.")
                print("   Try stopping other models or increasing node resources.")
            elif 'already exists' in error_msg.lower():
                print(f"⚠️  {start_name} model deployment already exists")
                # Try to get current status
                stats = es.ml.get_trained_models_stats(model_id=start_model)
                if stats['trained_model_stats']:
                    state = stats['trained_model_stats'][0].get('deployment_stats', {}).get('state', 'unknown')
                    print(f"   Current state: {state}")
            else:
                print(f"❌ Error starting {start_name} model: {error_msg[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error during model switch: {str(e)[:200]}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Check and manage Elasticsearch ML system status',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check status of all ML components
  python check_ml_status.py
  
  # Switch to NER model
  python check_ml_status.py --model ner
  
  # Switch to embedding model
  python check_ml_status.py --model embed
  
  # Export status to JSON
  python check_ml_status.py --export
  
  # Switch model and export status
  python check_ml_status.py --model ner --export
        """
    )
    
    parser.add_argument(
        '--model',
        choices=['ner', 'embed', 'embedding'],
        help='Switch to specified model (ner or embed)'
    )
    
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export status to JSON file'
    )
    
    args = parser.parse_args()
    
    print("🔍 Elasticsearch ML System Status Check")
    print("=" * 80)
    
    # Create Elasticsearch client
    es = create_elasticsearch_client()
    
    # Create status checker
    checker = MLStatusChecker(es)
    
    # Check connection first
    if not checker.check_elasticsearch_connection():
        print("❌ Cannot connect to Elasticsearch!")
        print(f"   URL: {ES_SCHEME}://{ES_HOST}:{ES_PORT}")
        print("   Please check your connection and credentials.")
        return 1
    
    # Switch model if requested
    if args.model:
        success = switch_model(es, args.model)
        if not success:
            print("\n⚠️  Model switch failed or partially completed")
            print("   Continuing with status check...")
        else:
            print("\n✅ Model switch completed successfully!")
        
        # Wait a moment for the switch to fully complete
        import time
        time.sleep(2)
    
    # Check all components
    print("\n⏳ Checking ML components...")
    checker.check_all_components()
    
    # Display status
    checker.display_status()
    
    # Export status if requested
    if args.export:
        checker.export_status()
    
    print("\n" + "=" * 80)
    print("✅ Status check complete!")
    
    # Return appropriate exit code
    if checker.status['summary']['fully_operational']:
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())