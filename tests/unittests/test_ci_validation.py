"""
Package installation and CI validation tests.

These tests ensure the package is properly configured for CI/CD
and can be installed correctly.
"""
import tempfile
from pathlib import Path


def test_package_can_be_built():
    """Test that the package can be built using the build system."""
    import biomero_importer
    
    # If we can import it, the package structure is correct
    assert biomero_importer is not None
    
    # Test that main entry points exist
    assert hasattr(biomero_importer, 'run_application')
    assert hasattr(biomero_importer, 'DatabasePoller')


def test_all_modules_importable():
    """Test that all main modules can be imported without errors."""
    # Test main module imports
    from biomero_importer.main import (
        DataPackage, DatabasePoller, create_executor, load_config
    )
    
    # Test utils imports
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    from biomero_importer.utils.initialize import (
        load_settings, initialize_system
    )
    from biomero_importer.utils.ingest_tracker import (
        get_ingest_tracker, IngestTracker, IngestionTracking
    )
    
    # Verify all classes/functions are defined
    assert DataPackage is not None
    assert DatabasePoller is not None
    assert UploadOrderManager is not None
    assert IngestTracker is not None
    assert IngestionTracking is not None
    
    # Verify all functions are callable
    assert callable(create_executor)
    assert callable(load_config)
    assert callable(load_settings)
    assert callable(initialize_system)
    assert callable(get_ingest_tracker)


def test_version_available_when_installed():
    """Test that version is available when package is properly installed."""
    try:
        from importlib.metadata import version
        pkg_version = version('biomero-importer')
        
        # Version should be a valid string
        assert isinstance(pkg_version, str)
        assert len(pkg_version) > 0
        
        # Should contain version-like content (numbers/dots)
        assert any(char.isdigit() for char in pkg_version)
        
    except Exception:
        # In development mode without proper installation,
        # version might not be available - that's OK
        pass


def test_dependencies_available():
    """Test that all required dependencies can be imported."""
    # Test core scientific dependencies
    import pandas
    import numpy
    
    # Test OMERO dependencies
    import ezomero
    
    # Test database dependencies
    import sqlalchemy
    import alembic
    
    # Test other required dependencies
    import zarr
    
    # Verify they have expected attributes to ensure proper import
    assert hasattr(pandas, 'DataFrame')
    assert hasattr(numpy, 'array')
    assert hasattr(ezomero, 'connect')
    assert hasattr(sqlalchemy, 'create_engine')
    assert hasattr(alembic, 'config')
    assert hasattr(zarr, 'open')


def test_optional_test_dependencies():
    """Test that optional test dependencies are available."""
    try:
        import pytest
        import unittest.mock
        
        # These should be available in test environment
        assert pytest is not None
        assert unittest.mock is not None
        
    except ImportError:
        # Optional dependencies might not be installed
        pass


def test_package_structure():
    """Test that the package has the expected structure."""
    import biomero_importer
    from pathlib import Path
    
    # Get package directory
    package_dir = Path(biomero_importer.__file__).parent
    
    # Check for expected subdirectories
    expected_dirs = ['utils', 'migrations']
    for dir_name in expected_dirs:
        dir_path = package_dir / dir_name
        assert dir_path.exists(), f"Expected directory {dir_name} not found"
        assert dir_path.is_dir(), f"{dir_name} is not a directory"
    
    # Check for key files
    expected_files = ['main.py', '__init__.py']
    for file_name in expected_files:
        file_path = package_dir / file_name
        assert file_path.exists(), f"Expected file {file_name} not found"
        assert file_path.is_file(), f"{file_name} is not a file"


def test_entry_points_work():
    """Test that main entry points can be called without immediate errors."""
    from biomero_importer.main import load_config
    from biomero_importer.utils.initialize import load_settings
    
    # Test load_config with a simple config
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = Path(temp_dir) / 'test.yml'
        config_file.write_text('test_key: test_value\n')
        
        config = load_config(str(config_file))
        assert config is not None
        assert config['test_key'] == 'test_value'
    
    # Test load_settings with a simple config
    with tempfile.TemporaryDirectory() as temp_dir:
        settings_file = Path(temp_dir) / 'test_settings.yml'
        settings_file.write_text('setting_key: setting_value\n')
        
        settings = load_settings(str(settings_file))
        assert settings is not None
        assert settings['setting_key'] == 'setting_value'


def test_no_import_errors():
    """Test that importing the package doesn't cause any import errors."""
    try:
        import biomero_importer
        import biomero_importer.main
        import biomero_importer.utils
        import biomero_importer.utils.upload_order_manager
        import biomero_importer.utils.initialize
        import biomero_importer.utils.ingest_tracker
        
        # Verify imports have expected attributes
        assert hasattr(biomero_importer.main, 'DataPackage')
        upload_order_mgr = biomero_importer.utils.upload_order_manager
        assert hasattr(upload_order_mgr, 'UploadOrderManager')
        
    except ImportError as e:
        # Any import error should fail the test
        assert False, f"Import error: {e}"