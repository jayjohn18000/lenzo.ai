# diagnostic_job_types.py
import sys

sys.path.append(".")

# Find and analyze QueryJob
try:
    # Try different import paths
    locations = [
        "backend.jobs.types",
        "backend.jobs",
        "backend.api.v1.types",
        "backend.types",
    ]

    QueryJob = None
    found_location = None

    for location in locations:
        try:
            module = __import__(location, fromlist=["QueryJob"])
            if hasattr(module, "QueryJob"):
                QueryJob = getattr(module, "QueryJob")
                found_location = location
                break
        except ImportError:
            continue

    if QueryJob:
        print(f"✓ Found QueryJob in {found_location}")

        # Analyze structure
        from dataclasses import is_dataclass, fields
        import inspect

        if is_dataclass(QueryJob):
            print("\nQueryJob dataclass fields:")
            for field in fields(QueryJob):
                default = (
                    f" = {field.default}"
                    if field.default is not field.default_factory
                    else ""
                )
                print(f"  {field.name}: {field.type}{default}")
        else:
            sig = inspect.signature(QueryJob)
            print(f"\nQueryJob constructor: {sig}")
    else:
        print("❌ Could not find QueryJob class")

except Exception as e:
    print(f"Error: {e}")
