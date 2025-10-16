"""
Integration tests for biomero_importer package.

These tests verify that the main components work together correctly
and that the package can be imported and used as expected.
"""
import pytest
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_package_import():
    """Test that the main package can be imported successfully."""
    import biomero_importer
    
    # With setuptools_scm, version is available through importlib.metadata
    try:
        from importlib.metadata import version
        pkg_version = version('biomero-importer')
        assert pkg_version is not None
        assert len(pkg_version) > 0
    except Exception:
        # If package not installed in development mode, skip version check
        pass
    
    # Ensure main components are accessible
    assert hasattr(biomero_importer, 'run_application')
    assert hasattr(biomero_importer, 'DatabasePoller')


def test_main_components_import():
    """Test that main components can be imported."""
    from biomero_importer.main import (
        DataPackage, DatabasePoller, create_executor
    )
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    from biomero_importer.utils.initialize import load_settings
    
    # Check that classes are properly defined
    assert DataPackage is not None
    assert DatabasePoller is not None
    assert UploadOrderManager is not None
    
    # Check that functions are callable
    assert callable(create_executor)
    assert callable(load_settings)


def test_data_package_integration():
    """Test DataPackage with realistic data."""
    from biomero_importer.main import DataPackage
    
    order_data = {
        'UUID': 'test-uuid-12345',
        'Username': 'testuser',
        'Group': 'testgroup',
        'DestinationID': 123,
        'DestinationType': 'Dataset',
        'Files': [
            '/path/to/file1.tif',
            '/path/to/file2.tif',
            '/path/to/file3.tif'
        ]
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_package = DataPackage(order_data, temp_dir)
        
        # Test basic functionality
        assert data_package.get('UUID') == 'test-uuid-12345'
        assert data_package.get('Username') == 'testuser'
        assert data_package.get('Group') == 'testgroup'
        assert data_package.get('DestinationID') == 123
        assert len(data_package.get('Files')) == 3
        
        # Test string representation
        str_repr = str(data_package)
        assert 'test-uuid-12345' in str_repr
        assert 'testuser' in str_repr


def test_upload_order_manager_integration():
    """Test UploadOrderManager with complete workflow."""
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    
    order_record = {
        'UUID': 'integration-test-uuid',
        'Username': 'integrationuser',
        'Group': 'Private',
        'DestinationID': 456,
        'DestinationType': 'Screen',
        'Files': [
            '/divg/testdata/image1.tif',
            '/divg/testdata/image2.tif'
        ]
    }
    
    config = {
        'log_file_path': '/tmp/test.log'
    }
    
    # Test normal operation
    manager = UploadOrderManager(order_record, config)
    order_info = manager.get_order_info()
    
    assert order_info['UUID'] == 'integration-test-uuid'
    assert order_info['DestinationType'] == 'Screen'
    assert order_info['DestinationID'] == 456
    assert len(order_info['Files']) == 2
    
    # Test path prefix switching
    manager.switch_path_prefix()
    updated_info = manager.get_order_info()
    
    for file_path in updated_info['Files']:
        starts_with_data = (file_path.startswith('/data/') or
                            file_path.startswith('\\data\\'))
        assert starts_with_data
        assert 'divg' not in file_path.lower()


def test_settings_loading_integration():
    """Test settings loading with real file operations."""
    from biomero_importer.utils.initialize import load_settings
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test YAML loading
        yaml_file = Path(temp_dir) / 'test_settings.yml'
        test_config = {
            'database': {
                'host': 'localhost',
                'port': 5432
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        with open(yaml_file, 'w') as f:
            yaml.dump(test_config, f)
        
        loaded_config = load_settings(str(yaml_file))
        assert loaded_config['database']['host'] == 'localhost'
        assert loaded_config['logging']['level'] == 'INFO'
        
        # Test JSON loading
        json_file = Path(temp_dir) / 'test_settings.json'
        with open(json_file, 'w') as f:
            json.dump(test_config, f)
        
        loaded_json_config = load_settings(str(json_file))
        assert loaded_json_config == test_config


def test_config_loading_integration():
    """Test main config loading functionality."""
    from biomero_importer.main import load_config
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = Path(temp_dir) / 'integration_test.yml'
        test_config = {
            'max_workers': 4,
            'log_level': 'DEBUG',
            'log_file_path': '/var/log/biomero.log'
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        loaded_config = load_config(str(config_file))
        assert loaded_config['max_workers'] == 4
        assert loaded_config['log_level'] == 'DEBUG'


def test_executor_creation_integration():
    """Test executor creation with real configuration."""
    from biomero_importer.main import create_executor
    
    config = {
        'max_workers': 2,
        'log_level': 'INFO',
        'log_file_path': '/tmp/test_executor.log'
    }
    
    with patch('biomero_importer.main.ProcessPoolExecutor') as mock_executor:
        mock_instance = MagicMock()
        mock_executor.return_value = mock_instance
        
        create_executor(config)
        
        # Verify executor was created with correct parameters
        mock_executor.assert_called_once()
        call_args = mock_executor.call_args
        assert call_args.kwargs['max_workers'] == 2
        assert 'initializer' in call_args.kwargs


def test_validation_errors():
    """Test that validation works correctly for invalid data."""
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    
    config = {'log_file_path': '/tmp/validation_test.log'}
    
    # Test missing required attributes
    incomplete_record = {
        'UUID': 'test-uuid',
        'Username': 'testuser'
        # Missing Group, DestinationID, DestinationType
    }
    
    with pytest.raises(ValueError, match="Missing required attributes"):
        UploadOrderManager(incomplete_record, config)
    
    # Test invalid DestinationType
    invalid_type_record = {
        'UUID': 'test-uuid',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 123,
        'DestinationType': 'InvalidType'  # Should be Dataset or Screen
    }
    
    with pytest.raises(ValueError, match="Invalid 'DestinationType'"):
        UploadOrderManager(invalid_type_record, config)
    
    # Test invalid DestinationID
    invalid_id_record = {
        'UUID': 'test-uuid',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 'not-a-number',  # Should be integer
        'DestinationType': 'Dataset'
    }
    
    with pytest.raises(ValueError, match="'DestinationID' must be a valid integer"):
        UploadOrderManager(invalid_id_record, config)


def test_file_name_formatting():
    """Test file name formatting functionality."""
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    
    config = {'log_file_path': '/tmp/filename_test.log'}
    
    # Test with many files (should get ellipsis formatting)
    many_files_record = {
        'UUID': 'test-uuid',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 123,
        'DestinationType': 'Dataset',
        'Files': [
            '/path/to/file1.tif',
            '/path/to/file2.tif',
            '/path/to/file3.tif',
            '/path/to/file4.tif',
            '/path/to/file5.tif'
        ]
    }
    
    manager = UploadOrderManager(many_files_record, config)
    order_info = manager.get_order_info()
    
    # Should format as [first, ..., last]
    assert order_info['FileNames'] == ['file1.tif', '...', 'file5.tif']
    
    # Test with few files (no ellipsis)
    few_files_record = {
        'UUID': 'test-uuid-2',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 123,
        'DestinationType': 'Dataset',
        'Files': [
            '/path/to/single_file.tif'
        ]
    }
    
    manager2 = UploadOrderManager(few_files_record, config)
    order_info2 = manager2.get_order_info()
    
    # Should show all files when only one
    assert order_info2['FileNames'] == ['single_file.tif']