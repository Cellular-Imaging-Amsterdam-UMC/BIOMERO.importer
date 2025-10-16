"""
Edge case and error handling tests for biomero_importer package.

These tests verify proper error handling, edge cases, and robustness
of the package under various conditions.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_data_package_with_missing_files():
    """Test DataPackage behavior when Files list is empty or missing."""
    from biomero_importer.main import DataPackage
    
    # Test with empty Files list
    order_data_empty = {
        'UUID': 'test-uuid',
        'Username': 'testuser',
        'Group': 'testgroup'
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_package = DataPackage(order_data_empty, temp_dir)
        assert data_package.get('Files') is None
        
        # Test with explicit empty list
        order_data_empty_list = order_data_empty.copy()
        order_data_empty_list['Files'] = []
        
        data_package_empty = DataPackage(order_data_empty_list, temp_dir)
        assert data_package_empty.get('Files') == []


def test_data_package_nonexistent_key():
    """Test DataPackage get method with non-existent keys."""
    from biomero_importer.main import DataPackage
    
    order_data = {
        'UUID': 'test-uuid',
        'Username': 'testuser'
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_package = DataPackage(order_data, temp_dir)
        
        # Test getting non-existent key without default
        assert data_package.get('NonExistentKey') is None
        
        # Test getting non-existent key with default
        assert data_package.get('NonExistentKey', 'default') == 'default'


def test_upload_order_manager_edge_case_validation():
    """Test UploadOrderManager validation with edge cases."""
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    
    config = {'log_file_path': '/tmp/edge_case_test.log'}
    
    # Test with DestinationID as string that can be converted to int
    convertible_record = {
        'UUID': 'test-uuid',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': '789',  # String that can be converted
        'DestinationType': 'Dataset'
    }
    
    manager = UploadOrderManager(convertible_record, config)
    order_info = manager.get_order_info()
    assert order_info['DestinationID'] == 789  # Should be converted to int
    assert isinstance(order_info['DestinationID'], int)
    
    # Test with DestinationID as float that can be converted to int
    float_record = {
        'UUID': 'test-uuid-2',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 456.0,  # Float that can be converted
        'DestinationType': 'Screen'
    }
    
    manager_float = UploadOrderManager(float_record, config)
    order_info_float = manager_float.get_order_info()
    assert order_info_float['DestinationID'] == 456
    assert isinstance(order_info_float['DestinationID'], int)


def test_settings_loading_with_invalid_files():
    """Test settings loading with various invalid file scenarios."""
    from biomero_importer.utils.initialize import load_settings
    
    # Test with non-existent file
    with pytest.raises(FileNotFoundError):
        load_settings('/path/that/does/not/exist.yml')
    
    # Test with unsupported file extension
    with tempfile.TemporaryDirectory() as temp_dir:
        invalid_file = Path(temp_dir) / 'test.txt'
        invalid_file.write_text('some content')
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_settings(str(invalid_file))
    
    # Test with malformed YAML
    with tempfile.TemporaryDirectory() as temp_dir:
        malformed_yaml = Path(temp_dir) / 'malformed.yml'
        malformed_yaml.write_text('invalid: yaml: content: [')
        
        with pytest.raises(Exception):  # YAML parsing error
            load_settings(str(malformed_yaml))
    
    # Test with malformed JSON
    with tempfile.TemporaryDirectory() as temp_dir:
        malformed_json = Path(temp_dir) / 'malformed.json'
        malformed_json.write_text('{"invalid": json,}')
        
        with pytest.raises(Exception):  # JSON parsing error
            load_settings(str(malformed_json))


def test_config_loading_edge_cases():
    """Test main config loading with edge cases."""
    from biomero_importer.main import load_config
    
    # Test with empty YAML file
    with tempfile.TemporaryDirectory() as temp_dir:
        empty_yaml = Path(temp_dir) / 'empty.yml'
        empty_yaml.write_text('')
        
        config = load_config(str(empty_yaml))
        assert config is None  # Empty YAML should return None
    
    # Test with YAML containing only comments
    with tempfile.TemporaryDirectory() as temp_dir:
        comment_yaml = Path(temp_dir) / 'comments.yml'
        comment_yaml.write_text('# This is just a comment\n# Another comment\n')
        
        config = load_config(str(comment_yaml))
        assert config is None


def test_path_switching_edge_cases():
    """Test path switching with various edge cases."""
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    
    config = {'log_file_path': '/tmp/path_test.log'}
    
    # Test with paths that don't have 'divg' component
    no_divg_record = {
        'UUID': 'test-uuid',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 123,
        'DestinationType': 'Dataset',
        'Files': [
            '/other/path/file1.tif',
            '/another/different/path/file2.tif'
        ]
    }
    
    manager = UploadOrderManager(no_divg_record, config)
    original_files = manager.get_order_info()['Files'].copy()
    
    manager.switch_path_prefix()
    switched_files = manager.get_order_info()['Files']
    
    # Files without 'divg' should remain unchanged
    assert switched_files == original_files
    
    # Test with mixed case 'DIVG'
    mixed_case_record = {
        'UUID': 'test-uuid-2',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 123,
        'DestinationType': 'Dataset',
        'Files': [
            '/DIVG/mixed/case/file.tif',
            '/DiVg/another/file.tif'
        ]
    }
    
    manager_mixed = UploadOrderManager(mixed_case_record, config)
    manager_mixed.switch_path_prefix()
    mixed_files = manager_mixed.get_order_info()['Files']
    
    # Should handle case-insensitive matching
    for file_path in mixed_files:
        if 'mixed' in file_path or 'another' in file_path:
            # Use os.path.normpath to handle different separators
            normalized = os.path.normpath(file_path)
            assert normalized.startswith(os.path.normpath('/data'))


def test_file_names_formatting_edge_cases():
    """Test file name formatting with various edge cases."""
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    
    config = {'log_file_path': '/tmp/filename_edge_test.log'}
    
    # Test with exactly 2 files (boundary case)
    two_files_record = {
        'UUID': 'test-uuid',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 123,
        'DestinationType': 'Dataset',
        'Files': [
            '/path/to/first.tif',
            '/path/to/second.tif'
        ]
    }
    
    manager = UploadOrderManager(two_files_record, config)
    order_info = manager.get_order_info()
    
    # With 2 files, should show both (no ellipsis)
    assert order_info['FileNames'] == ['first.tif', 'second.tif']
    
    # Test with no Files attribute
    no_files_record = {
        'UUID': 'test-uuid-2',
        'Username': 'testuser',
        'Group': 'Private',
        'DestinationID': 123,
        'DestinationType': 'Dataset'
        # No Files attribute
    }
    
    manager_no_files = UploadOrderManager(no_files_record, config)
    order_info_no_files = manager_no_files.get_order_info()
    
    # Should create empty FileNames list
    assert order_info_no_files['FileNames'] == []


def test_logging_integration():
    """Test that logging is properly configured and used."""
    from biomero_importer.utils.upload_order_manager import UploadOrderManager
    
    config = {'log_file_path': '/tmp/logging_test.log'}
    
    # Capture log messages
    with patch('biomero_importer.utils.upload_order_manager.logging') as mock_logging:
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        
        valid_record = {
            'UUID': 'test-uuid',
            'Username': 'testuser',
            'Group': 'Private',
            'DestinationID': 123,
            'DestinationType': 'Dataset',
            'Files': ['/path/to/file.tif']
        }
        
        UploadOrderManager(valid_record, config)
        
        # Verify logging calls were made
        mock_logging.getLogger.assert_called()
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()


def test_database_poller_initialization():
    """Test DatabasePoller can be initialized properly."""
    from biomero_importer.main import DatabasePoller
    
    config = {
        'database_poll_interval': 5,
        'max_workers': 2
    }
    mock_executor = MagicMock()
    
    # Test that DatabasePoller can be instantiated
    with patch('biomero_importer.main.logging.getLogger'), \
         patch('biomero_importer.main.get_ingest_tracker') as mock_get_tracker:
        
        # Mock the ingest tracker with required attributes
        mock_tracker = MagicMock()
        mock_tracker.engine = MagicMock()
        mock_get_tracker.return_value = mock_tracker
        
        poller = DatabasePoller(config, mock_executor)
        assert poller is not None
        assert hasattr(poller, 'start')
        assert hasattr(poller, 'stop')


def test_thread_safety_considerations():
    """Test thread safety aspects of key components."""
    from biomero_importer.main import DataPackage
    import threading
    import time
    
    order_data = {
        'UUID': 'thread-test-uuid',
        'Username': 'threaduser',
        'Group': 'Private',
        'counter': 0
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_package = DataPackage(order_data, temp_dir)
        results = []
        
        def worker():
            # Simulate concurrent access
            for i in range(10):
                uuid_val = data_package.get('UUID')
                results.append(uuid_val)
                # Small delay to increase chance of race conditions
                time.sleep(0.001)
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # All results should be consistent
        assert all(result == 'thread-test-uuid' for result in results)
        assert len(results) == 30  # 3 threads × 10 iterations each