from backend.query_engine import get_query_engine

# Test the query
query_engine = get_query_engine()

question = "2월에 코스트코에 총 얼마나 썼어?"
user_id = 3

result = query_engine.query(
    question=question,
    user_id=user_id,
    top_k=20
)

print("=" * 80)
print(f"Question: {question}")
print(f"Answer: {result['answer']}")
print(f"\nNumber of sources: {len(result['sources'])}")
print(f"Retrieval time: {result['retrieval_time']:.3f}s")
print("\nSources:")
for i, source in enumerate(result['sources'], 1):
    print(f"\n{i}. {source['filename']}")
    print(f"   Score: {source['score']}")
    print(f"   Metadata:")
    for key, value in source['metadata'].items():
        print(f"     {key}: {value}")
    print(f"   Content preview: {source['chunk'][:150]}...")
