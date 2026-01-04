import asyncio
import os
import sys

# Add backend directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '../'))
sys.path.append(backend_dir)

from lightweight.services.data_collection_worker import generate_research_dataset
from lightweight.services.chapter4_generator import generate_chapter4
from lightweight.services.chapter5_generator_v2 import generate_chapter5_v2
from lightweight.services.chapter6_generator import generate_chapter6

async def main():
    print("🧪 Verifying generators with extra kwargs...")
    
    extra_args = {"thesis_type": "phd", "random_arg": 123}
    
    try:
        print("1. Testing generate_research_dataset...")
        # Mocking implementation to avoid actual heavy work if possible, but python functions are imported.
        # We just want to check signature acceptance.
        # We invoke it but expect it might fail inside due to missing deps/paths, but NOT TypeError on arguments.
        try:
            await generate_research_dataset(
                topic="Test", 
                case_study="Test Case", # Added
                output_dir="/tmp",
                **extra_args
            )
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"❌ FAILED generate_research_dataset: {e}")
                return
            print(f"⚠️ Runtime error (expected): {e}")
        except Exception as e:
             print(f"⚠️ Runtime error (expected): {e}")
            
        print("✅ generate_research_dataset signature OK")
        
        print("2. Testing generate_chapter4...")
        try:
            await generate_chapter4(
                topic="Test",
                case_study="Test Case",
                objectives=["Obj1"],
                **extra_args
            )
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"❌ FAILED generate_chapter4: {e}")
                return
            print(f"⚠️ Runtime error (expected): {e}")
        except Exception as e:
             print(f"⚠️ Runtime error (expected): {e}")
             
        print("✅ generate_chapter4 signature OK")
        
        print("3. Testing generate_chapter5_v2...")
        try:
            await generate_chapter5_v2(
                topic="Test",
                case_study="Test Case",
                objectives=["Obj1"],
                **extra_args
            )
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"❌ FAILED generate_chapter5_v2: {e}")
                return
            print(f"⚠️ Runtime error (expected): {e}")
        except Exception as e:
             print(f"⚠️ Runtime error (expected): {e}")
        
        print("✅ generate_chapter5_v2 signature OK")
        
        print("4. Testing generate_chapter6...")
        try:
            # Sync function
            generate_chapter6(
                topic="Test",
                case_study="Test Case",
                objectives=["Obj1"],
                **extra_args
            )
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                print(f"❌ FAILED generate_chapter6: {e}")
                return
            print(f"⚠️ Runtime error (expected): {e}")
        except Exception as e:
             print(f"⚠️ Runtime error (expected): {e}")

        print("✅ generate_chapter6 signature OK")
        
        print("\n🎉 ALL SIGNATURE VERIFICATION PASSED")
        
    except Exception as e:
        print(f"❌ Verification script crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
