import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.app.services.knowledge_graph_service import get_knowledge_graph_service

async def test_kg():
    print("Testing Knowledge Graph Connection...")
    try:
        service = get_knowledge_graph_service()
        driver = await service._get_driver()
        print("Driver created.")
        async with driver.session() as session:
            result = await session.run("RETURN 1 as val")
            record = await result.single()
            print(f"Query result: {record['val']}")
        print("Connection successful.")
        
        # Test adding entity
        print("Testing add_entity...")
        props = {"id": "test_node", "name": "Test Node"}
        await service.add_entity("TestLabel", props)
        print("Entity added.")
        
    except Exception as e:
        print(f"KG Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_kg())
