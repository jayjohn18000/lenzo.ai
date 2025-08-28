#!/usr/bin/env python3
# backend/scripts/init_db.py
"""Initialize NextAGI SQLite database with proper schema"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
from backend.database.models import init_db, get_session, QueryRequest, ModelResponse

def create_tables():
    """Create all database tables"""
    print("🔨 Creating database tables...")
    engine = init_db()
    print("✅ Database tables created successfully!")
    return engine

def check_existing_data(session):
    """Check if data already exists"""
    count = session.query(QueryRequest).count()
    if count > 0:
        response = input(f"\n⚠️  Found {count} existing records. Clear and start fresh? (y/n): ")
        if response.lower() == 'y':
            session.query(ModelResponse).delete()
            session.query(QueryRequest).delete()
            session.commit()
            print("🗑️  Existing data cleared.")
            return True
    return False

def add_sample_data(session):
    """Add some sample data for testing (optional)"""
    response = input("\n💾 Add sample data for testing? (y/n): ")
    if response.lower() != 'y':
        return
    
    print("📝 Adding sample data...")
    
    sample_prompts = [
        "What are the key principles of machine learning?",
        "Explain quantum computing in simple terms",
        "How does blockchain technology work?",
        "What is the difference between AI and ML?",
        "Best practices for API security"
    ]
    
    models = [
        "openai/gpt-4o",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-pro-1.5",
        "openai/gpt-4o-mini"
    ]
    
    # Generate sample data for the past 7 days
    for days_ago in range(7, -1, -1):
        date = datetime.utcnow() - timedelta(days=days_ago)
        
        # Generate 5-15 queries per day
        num_queries = random.randint(5, 15)
        
        for _ in range(num_queries):
            prompt = random.choice(sample_prompts)
            mode = random.choice(["speed", "quality", "balanced"])
            selected_models = random.sample(models, k=random.randint(2, 4))
            
            # Create query request
            query = QueryRequest(
                request_id=f"sample-{date.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                prompt=prompt,
                mode=mode,
                max_models=len(selected_models),
                created_at=date,
                response_time_ms=random.randint(1500, 4000),
                total_tokens_used=random.randint(300, 1000),
                total_cost=round(random.uniform(0.01, 0.10), 4),
                winner_confidence=round(random.uniform(0.75, 0.95), 3),  # Properly bounded
                winner_model=random.choice(selected_models)
            )
            query.models_used = selected_models
            session.add(query)
            
            # Create model responses
            winner_selected = False
            for i, model in enumerate(selected_models):
                is_winner = (model == query.winner_model) and not winner_selected
                if is_winner:
                    winner_selected = True
                
                # Generate bounded confidence scores
                base_confidence = random.uniform(0.7, 0.9)
                if is_winner:
                    confidence = min(1.0, base_confidence + 0.05)  # Winner boost, but bounded
                else:
                    confidence = base_confidence
                
                response = ModelResponse(
                    request_id=query.request_id,
                    model_name=model,
                    response_text=f"Sample response from {model} for: {prompt[:50]}...",
                    confidence_score=confidence,
                    response_time_ms=random.randint(800, 3000),
                    tokens_used=random.randint(150, 400),
                    cost=round(random.uniform(0.005, 0.05), 4),
                    reliability_score=round(random.uniform(0.75, 0.95), 3),
                    consistency_score=round(random.uniform(0.70, 0.90), 3),
                    hallucination_risk=round(random.uniform(0.05, 0.25), 3),
                    citation_quality=round(random.uniform(0.60, 0.85), 3),
                    rank_position=i + 1,
                    is_winner=is_winner,
                    created_at=date
                )
                response.trait_scores = {
                    "accuracy": round(random.uniform(0.75, 0.95), 3),
                    "clarity": round(random.uniform(0.70, 0.90), 3),
                    "completeness": round(random.uniform(0.65, 0.88), 3)
                }
                session.add(response)
    
    session.commit()
    print(f"✅ Added sample data for {session.query(QueryRequest).count()} queries")

def verify_data(session):
    """Verify data integrity"""
    print("\n🔍 Verifying data integrity...")
    
    # Check for confidence values > 1.0
    over_confidence = session.query(ModelResponse).filter(ModelResponse.confidence_score > 1.0).count()
    if over_confidence > 0:
        print(f"❌ Found {over_confidence} records with confidence > 1.0!")
    
    # Check for negative confidence
    negative_confidence = session.query(ModelResponse).filter(ModelResponse.confidence_score < 0.0).count()
    if negative_confidence > 0:
        print(f"❌ Found {negative_confidence} records with confidence < 0.0!")
    
    # Get statistics
    total_queries = session.query(QueryRequest).count()
    total_responses = session.query(ModelResponse).count()
    avg_confidence = session.query(func.avg(ModelResponse.confidence_score)).scalar()
    
    print(f"\n📊 Database Statistics:")
    print(f"  • Total queries: {total_queries}")
    print(f"  • Total model responses: {total_responses}")
    print(f"  • Average confidence: {avg_confidence:.3f}" if avg_confidence else "  • No data")
    
    # Show confidence distribution
    print("\n📈 Confidence Distribution:")
    ranges = [
        (0.0, 0.5, "Low (0-50%)"),
        (0.5, 0.7, "Medium (50-70%)"),
        (0.7, 0.9, "High (70-90%)"),
        (0.9, 1.0, "Very High (90-100%)")
    ]
    
    for min_val, max_val, label in ranges:
        count = session.query(ModelResponse).filter(
            ModelResponse.confidence_score >= min_val,
            ModelResponse.confidence_score <= max_val
        ).count()
        print(f"  • {label}: {count} responses")

def main():
    """Main initialization function"""
    print("🚀 NextAGI Database Initialization")
    print("=" * 50)
    
    try:
        # Create tables
        engine = create_tables()
        session = get_session(engine)
        
        # Check existing data
        check_existing_data(session)
        
        # Add sample data if requested
        add_sample_data(session)
        
        # Verify data integrity
        from sqlalchemy import func
        verify_data(session)
        
        print("\n✨ Database initialization complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()