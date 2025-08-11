"""SessionFileConfig 单元测试"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, mock_open

from src.config.session_config import SessionFileConfig


class TestSessionFileConfig:
    """SessionFileConfig 测试类"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录用于测试"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def session_config(self, temp_dir):
        """创建 SessionFileConfig 实例"""
        return SessionFileConfig(temp_dir)
    
    def test_init_creates_config_file_if_not_exists(self, temp_dir):
        """测试初始化时如果配置文件不存在则创建"""
        config_path = os.path.join(temp_dir, '.session_files.json')
        assert not os.path.exists(config_path)
        
        SessionFileConfig(temp_dir)
        
        assert os.path.exists(config_path)
    
    def test_init_loads_existing_config_file(self, temp_dir):
        """测试初始化时加载已存在的配置文件"""
        config_path = os.path.join(temp_dir, '.session_files.json')
        test_data = '{"test_file": "test.txt"}'
        
        with open(config_path, 'w') as f:
            f.write(test_data)
        
        config = SessionFileConfig(temp_dir)
        
        assert config.has_file('test_file')
        assert config.get_filename('test_file') == 'test.txt'
    
    def test_add_file_stores_file_mapping(self, session_config):
        """测试添加文件映射"""
        file_id = 'test_file_123'
        filename = 'example.py'
        
        session_config.add_file(file_id, filename)
        
        assert session_config.has_file(file_id)
        assert session_config.get_filename(file_id) == filename
    
    def test_add_file_overwrites_existing_mapping(self, session_config):
        """测试添加文件时覆盖已存在的映射"""
        file_id = 'test_file'
        old_filename = 'old.py'
        new_filename = 'new.py'
        
        session_config.add_file(file_id, old_filename)
        session_config.add_file(file_id, new_filename)
        
        assert session_config.get_filename(file_id) == new_filename
    
    def test_has_file_returns_true_for_existing_file(self, session_config):
        """测试检查文件存在性返回True"""
        file_id = 'existing_file'
        filename = 'test.txt'
        
        session_config.add_file(file_id, filename)
        
        assert session_config.has_file(file_id) is True
    
    def test_has_file_returns_false_for_nonexistent_file(self, session_config):
        """测试检查不存在文件返回False"""
        assert session_config.has_file('nonexistent_file') is False
    
    def test_get_filename_returns_correct_filename(self, session_config):
        """测试获取文件名返回正确结果"""
        file_id = 'test_file'
        filename = 'document.pdf'
        
        session_config.add_file(file_id, filename)
        
        assert session_config.get_filename(file_id) == filename
    
    def test_get_filename_returns_none_for_nonexistent_file(self, session_config):
        """测试获取不存在文件名返回None"""
        assert session_config.get_filename('nonexistent_file') is None
    
    def test_remove_file_deletes_mapping(self, session_config):
        """测试删除文件映射"""
        file_id = 'temp_file'
        filename = 'temp.txt'
        
        session_config.add_file(file_id, filename)
        assert session_config.has_file(file_id)
        
        session_config.remove_file(file_id)
        
        assert not session_config.has_file(file_id)
        assert session_config.get_filename(file_id) is None
    
    def test_remove_nonexistent_file_does_not_raise_error(self, session_config):
        """测试删除不存在的文件不会抛出错误"""
        # 应该不抛出异常
        session_config.remove_file('nonexistent_file')
    
    def test_clear_all_files_removes_all_mappings(self, session_config):
        """测试清空所有文件映射"""
        session_config.add_file('file1', 'test1.txt')
        session_config.add_file('file2', 'test2.txt')
        session_config.add_file('file3', 'test3.txt')
        
        assert session_config.has_file('file1')
        assert session_config.has_file('file2')
        assert session_config.has_file('file3')
        
        session_config.clear_all_files()
        
        assert not session_config.has_file('file1')
        assert not session_config.has_file('file2')
        assert not session_config.has_file('file3')
    
    def test_save_persists_changes_to_disk(self, temp_dir):
        """测试保存操作将更改持久化到磁盘"""
        config1 = SessionFileConfig(temp_dir)
        config1.add_file('persistent_file', 'persistent.txt')
        
        # 创建新实例来验证持久化
        config2 = SessionFileConfig(temp_dir)
        
        assert config2.has_file('persistent_file')
        assert config2.get_filename('persistent_file') == 'persistent.txt'
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_save_handles_io_error_gracefully(self, mock_file, session_config):
        """测试保存时IO错误的优雅处理"""
        session_config.add_file('test', 'test.txt')
        
        # add_file方法内部会调用_save_config，应该不抛出异常
        # 这里我们只是验证不会崩溃
        pass
    
    def test_config_file_path_is_correct(self, temp_dir):
        """测试配置文件路径正确"""
        config = SessionFileConfig(temp_dir)
        expected_path = os.path.join(temp_dir, '.session_files.json')
        
        assert config.config_path == expected_path
    
    def test_multiple_operations_maintain_consistency(self, session_config):
        """测试多个操作保持数据一致性"""
        # 添加多个文件
        session_config.add_file('file1', 'test1.txt')
        session_config.add_file('file2', 'test2.txt')
        session_config.add_file('file3', 'test3.txt')
        
        # 删除一个文件
        session_config.remove_file('file2')
        
        # 修改一个文件
        session_config.add_file('file1', 'modified1.txt')
        
        # 验证最终状态
        assert session_config.has_file('file1')
        assert session_config.get_filename('file1') == 'modified1.txt'
        assert not session_config.has_file('file2')
        assert session_config.has_file('file3')
        assert session_config.get_filename('file3') == 'test3.txt'
    
    def test_empty_session_directory_handling(self):
        """测试空会话目录的处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SessionFileConfig(temp_dir)
            
            # 空配置应该正常工作
            assert not config.has_file('any_file')
            assert config.get_filename('any_file') is None
            
            # 添加文件应该正常工作
            config.add_file('test', 'test.txt')
            assert config.has_file('test')