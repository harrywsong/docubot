"""
Export processed documents for Raspberry Pi deployment.

This script processes all documents on your powerful desktop and exports
the vector store and database for deployment on a Raspberry Pi.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import Config
from backend.vector_store import VectorStore
from backend.database import DatabaseManager
from backend.export_manager import ExportManager


def export_data(output_dir: str = "pi_export", incremental: bool = False, since: str = None):
    """
    Export ChromaDB vector store and SQLite database for Pi deployment.
    
    Args:
        output_dir: Directory to export data to
        incremental: If True, create incremental export with only new/modified data
        since: ISO format timestamp for incremental exports (e.g., "2024-01-15T10:30:00")
    """
    print("=" * 80)
    print("Exporting Data for Raspberry Pi Deployment")
    print("=" * 80)
    
    # Parse since timestamp if provided
    since_timestamp = None
    if since:
        try:
            since_timestamp = datetime.fromisoformat(since)
            print(f"\nIncremental export since: {since_timestamp}")
        except ValueError:
            print(f"\n✗ Invalid timestamp format: {since}")
            print("  Expected ISO format: YYYY-MM-DDTHH:MM:SS")
            return False
    
    # Initialize components
    print("\nInitializing components...")
    try:
        vector_store = VectorStore(persist_directory=Config.CHROMADB_PATH)
        db_manager = DatabaseManager(db_path=Config.SQLITE_PATH)
        export_manager = ExportManager(Config, vector_store, db_manager)
        print("✓ Components initialized")
    except Exception as e:
        print(f"✗ Failed to initialize components: {e}")
        return False
    
    # Create export package using ExportManager
    print(f"\nCreating {'incremental' if incremental else 'full'} export package...")
    result = export_manager.create_export_package(
        output_dir=output_dir,
        incremental=incremental,
        since_timestamp=since_timestamp
    )
    
    # Check if export was successful
    if not result.success:
        print("\n" + "=" * 80)
        print("Export Failed!")
        print("=" * 80)
        print("\nErrors:")
        for error in result.errors:
            print(f"  ✗ {error}")
        print("=" * 80)
        return False
    
    # Display success information
    print("\n" + "=" * 80)
    print("Export Complete!")
    print("=" * 80)
    print(f"\nExport package: {result.package_path}")
    print(f"Archive: {result.archive_path}")
    print(f"Size: {result.size_bytes / (1024*1024):.2f} MB")
    
    # Display statistics
    print("\nStatistics:")
    stats = result.statistics
    if incremental:
        print(f"  • New documents: {stats.get('new_documents', 0)}")
        print(f"  • New chunks: {stats.get('new_chunks', 0)}")
    else:
        print(f"  • Total documents: {stats.get('total_documents', 0)}")
        print(f"  • Total chunks: {stats.get('total_chunks', 0)}")
        print(f"  • Total embeddings: {stats.get('total_embeddings', 0)}")
    
    print(f"  • Vector store size: {stats.get('vector_store_size_mb', 0):.2f} MB")
    print(f"  • Database size: {stats.get('database_size_mb', 0):.2f} MB")
    
    # Display next steps
    print("\nNext steps:")
    print(f"1. Copy {Path(result.archive_path).name} to your Raspberry Pi")
    print(f"2. Follow instructions in {result.package_path}/DEPLOYMENT.md")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Export data for Raspberry Pi deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full export (default)
  python utils/export_for_pi.py
  
  # Full export to custom directory
  python utils/export_for_pi.py --output my_export
  
  # Incremental export (only new/modified data)
  python utils/export_for_pi.py --incremental
  
  # Incremental export since specific timestamp
  python utils/export_for_pi.py --incremental --since "2024-01-15T10:30:00"
        """
    )
    parser.add_argument(
        "--output",
        default="pi_export",
        help="Output directory for export package (default: pi_export)"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Create incremental export with only new/modified data"
    )
    parser.add_argument(
        "--since",
        help="ISO format timestamp for incremental exports (e.g., 2024-01-15T10:30:00)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.since and not args.incremental:
        print("Error: --since can only be used with --incremental")
        sys.exit(1)
    
    success = export_data(
        output_dir=args.output,
        incremental=args.incremental,
        since=args.since
    )
    sys.exit(0 if success else 1)
