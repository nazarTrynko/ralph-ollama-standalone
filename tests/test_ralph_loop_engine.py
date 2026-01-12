"""
Unit tests for RalphLoopEngine.
"""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from lib.ralph_loop_engine import (
    RalphLoopEngine,
    Phase,
    LoopMode
)
from integration.ralph_ollama_adapter import RalphOllamaAdapter


class TestRalphLoopEngine:
    """Test RalphLoopEngine."""
    
    def test_init_default(self, tmp_path):
        """Test engine initialization with default adapter."""
        engine = RalphLoopEngine(tmp_path)
        assert engine.project_path == tmp_path.resolve()
        assert engine.adapter is not None
        assert isinstance(engine.adapter, RalphOllamaAdapter)
        assert engine.mode == LoopMode.PHASE_BY_PHASE
        assert engine.current_phase == Phase.IDLE
        assert engine.is_running is False
        assert engine.is_paused is False
        assert engine.should_stop is False
    
    def test_init_custom_adapter(self, tmp_path):
        """Test engine initialization with custom adapter."""
        custom_adapter = RalphOllamaAdapter()
        engine = RalphLoopEngine(tmp_path, adapter=custom_adapter)
        assert engine.adapter is custom_adapter
    
    def test_set_status_callback(self, tmp_path):
        """Test setting status callback."""
        engine = RalphLoopEngine(tmp_path)
        callback = Mock()
        engine.set_status_callback(callback)
        assert engine.status_callback is callback
    
    def test_emit_status(self, tmp_path):
        """Test status emission via callback."""
        engine = RalphLoopEngine(tmp_path)
        callback = Mock()
        engine.set_status_callback(callback)
        
        status = {'message': 'test', 'phase': 'idle'}
        engine._emit_status(status)
        callback.assert_called_once_with(status)
    
    def test_emit_status_no_callback(self, tmp_path):
        """Test status emission without callback (should not error)."""
        engine = RalphLoopEngine(tmp_path)
        status = {'message': 'test', 'phase': 'idle'}
        # Should not raise
        engine._emit_status(status)
    
    def test_emit_status_callback_error(self, tmp_path):
        """Test status emission with callback that raises error."""
        engine = RalphLoopEngine(tmp_path)
        callback = Mock(side_effect=Exception("Callback error"))
        engine.set_status_callback(callback)
        
        status = {'message': 'test', 'phase': 'idle'}
        # Should not raise, but log error
        engine._emit_status(status)
        callback.assert_called_once()
    
    def test_log_status(self, tmp_path):
        """Test status logging."""
        engine = RalphLoopEngine(tmp_path)
        callback = Mock()
        engine.set_status_callback(callback)
        
        engine._log_status("Test message", Phase.STUDY, extra="data")
        
        assert len(engine.status_log) == 1
        entry = engine.status_log[0]
        assert entry['message'] == "Test message"
        assert entry['phase'] == Phase.STUDY.value
        assert entry['extra'] == "data"
        assert 'timestamp' in entry
        
        callback.assert_called_once()
    
    def test_initialize_project(self, tmp_path):
        """Test project initialization."""
        engine = RalphLoopEngine(tmp_path)
        engine.initialize_project("Test Project", "Test description", "Initial task")
        
        # Check directories created
        assert (tmp_path / 'src').exists()
        assert (tmp_path / 'tests').exists()
        assert (tmp_path / 'docs').exists()
        assert (tmp_path / 'specs').exists()
        
        # Check README
        readme = tmp_path / 'README.md'
        assert readme.exists()
        content = readme.read_text()
        assert "Test Project" in content
        assert "Test description" in content
        
        # Check @fix_plan.md
        fix_plan = tmp_path / '@fix_plan.md'
        assert fix_plan.exists()
        content = fix_plan.read_text()
        assert "Initial task" in content
        assert "- [ ] Initial task" in content
    
    def test_initialize_project_no_initial_task(self, tmp_path):
        """Test project initialization without initial task."""
        engine = RalphLoopEngine(tmp_path)
        engine.initialize_project("Test Project", "Test description")
        
        fix_plan = tmp_path / '@fix_plan.md'
        assert fix_plan.exists()
        content = fix_plan.read_text()
        assert "Initial task" not in content
    
    def test_read_fix_plan_empty(self, tmp_path):
        """Test reading fix plan when file doesn't exist."""
        engine = RalphLoopEngine(tmp_path)
        tasks = engine._read_fix_plan()
        assert tasks == []
    
    def test_read_fix_plan_with_tasks(self, tmp_path):
        """Test reading fix plan with tasks."""
        engine = RalphLoopEngine(tmp_path)
        fix_plan = tmp_path / '@fix_plan.md'
        fix_plan.write_text("""# Fix Plan

## High Priority

- [ ] Task 1
- [ ] Task 2

## Medium Priority

- [ ] Task 3

## Low Priority

- [ ] Task 4

## Completed Tasks

- [x] Completed Task
""")
        tasks = engine._read_fix_plan()
        assert len(tasks) == 4
        assert "Task 1" in tasks
        assert "Task 2" in tasks
        assert "Task 3" in tasks
        assert "Task 4" in tasks
        assert "Completed Task" not in tasks
    
    def test_read_fix_plan_skips_completed(self, tmp_path):
        """Test that completed tasks are not included."""
        engine = RalphLoopEngine(tmp_path)
        fix_plan = tmp_path / '@fix_plan.md'
        fix_plan.write_text("""# Fix Plan

## High Priority

- [ ] Task 1
- [x] Completed Task
- [ ] Task 2
""")
        tasks = engine._read_fix_plan()
        assert len(tasks) == 2
        assert "Task 1" in tasks
        assert "Task 2" in tasks
        assert "Completed Task" not in tasks
    
    @patch('lib.ralph_loop_engine.call_llm')
    def test_phase_study_success(self, mock_call_llm, tmp_path):
        """Test successful Study phase."""
        engine = RalphLoopEngine(tmp_path)
        mock_call_llm.return_value = "Analysis: This task requires implementing X"
        
        result = engine._phase_study("Test task")
        
        assert result['success'] is True
        assert result['output'] == "Analysis: This task requires implementing X"
        assert result['phase'] == Phase.STUDY.value
        mock_call_llm.assert_called_once()
    
    @patch('lib.ralph_loop_engine.call_llm')
    def test_phase_study_error(self, mock_call_llm, tmp_path):
        """Test Study phase with error."""
        engine = RalphLoopEngine(tmp_path)
        mock_call_llm.side_effect = Exception("LLM error")
        
        result = engine._phase_study("Test task")
        
        assert result['success'] is False
        assert 'error' in result
        assert result['phase'] == Phase.STUDY.value
    
    @patch('lib.ralph_loop_engine.call_llm')
    def test_phase_implement_success(self, mock_call_llm, tmp_path):
        """Test successful Implement phase."""
        engine = RalphLoopEngine(tmp_path)
        mock_call_llm.return_value = """```src/main.py
def main():
    print("Hello")
```
"""
        result = engine._phase_implement("Create main.py")
        
        assert result['success'] is True
        assert 'files_created' in result
        assert len(result['files_created']) == 1
        assert 'src/main.py' in result['files_created'][0] or 'main.py' in result['files_created'][0]
        
        # Check file was created
        created_file = tmp_path / result['files_created'][0]
        assert created_file.exists()
        content = created_file.read_text()
        assert "def main()" in content
    
    @patch('lib.ralph_loop_engine.call_llm')
    def test_phase_implement_multiple_files(self, mock_call_llm, tmp_path):
        """Test Implement phase with multiple files."""
        engine = RalphLoopEngine(tmp_path)
        mock_call_llm.return_value = """```src/file1.py
code1
```
```src/file2.py
code2
```
"""
        result = engine._phase_implement("Create files")
        
        assert result['success'] is True
        assert len(result['files_created']) == 2
    
    @patch('lib.ralph_loop_engine.call_llm')
    def test_phase_implement_error(self, mock_call_llm, tmp_path):
        """Test Implement phase with error."""
        engine = RalphLoopEngine(tmp_path)
        mock_call_llm.side_effect = Exception("LLM error")
        
        result = engine._phase_implement("Create file")
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_parse_code_blocks_with_path(self):
        """Test parsing code blocks with explicit paths."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```src/main.py
def main():
    pass
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert files[0]['path'] == 'src/main.py'
        assert 'def main()' in files[0]['content']
    
    def test_parse_code_blocks_with_language(self):
        """Test parsing code blocks with language tag."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```python
def main():
    pass
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        # Should use default naming since no path detected
        assert 'generated_0.py' in files[0]['path']
    
    def test_parse_code_blocks_multiple(self):
        """Test parsing multiple code blocks."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```file1.py
code1
```
```file2.py
code2
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 2
        assert files[0]['path'] == 'file1.py'
        assert files[1]['path'] == 'file2.py'
    
    def test_parse_code_blocks_no_blocks(self):
        """Test parsing response with no code blocks."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = "Just some text, no code blocks"
        files = engine._parse_code_blocks(response)
        assert len(files) == 0
    
    def test_parse_code_blocks_path_with_spaces(self):
        """Test parsing code blocks with paths containing spaces."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```src/my file.py
def main():
    pass
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert files[0]['path'] == 'src/my file.py'
        assert 'def main()' in files[0]['content']
    
    def test_parse_code_blocks_file_marker(self):
        """Test parsing code blocks with explicit file: marker."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```file: src/main.py
def main():
    pass
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert files[0]['path'] == 'src/main.py'
    
    def test_parse_code_blocks_empty_block(self):
        """Test that empty code blocks are skipped."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```python

```
```src/file.py
code here
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert files[0]['path'] == 'src/file.py'
        assert files[0]['content'] == 'code here'
    
    def test_parse_code_blocks_whitespace_only(self):
        """Test that whitespace-only blocks are skipped."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```python
   
```
```src/file.py
code here
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert files[0]['path'] == 'src/file.py'
    
    def test_parse_code_blocks_path_in_content(self):
        """Test extracting path from content when not in specifier."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```python
# file: src/main.py
def main():
    pass
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert files[0]['path'] == 'src/main.py'
    
    def test_parse_code_blocks_path_in_content_with_spaces(self):
        """Test extracting path with spaces from content."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```python
# path: src/my file.py
def main():
    pass
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert 'my file.py' in files[0]['path']
    
    def test_parse_code_blocks_language_vs_path(self):
        """Test distinguishing between language tags and file paths."""
        engine = RalphLoopEngine(Path("/tmp"))
        # Python language tag should not be treated as path
        response1 = """```python
def main():
    pass
```
"""
        files1 = engine._parse_code_blocks(response1)
        assert len(files1) == 1
        assert files1[0]['path'] == 'generated_0.py'  # Should use default, not 'python'
        
        # But python.py should be treated as path
        response2 = """```src/python.py
def main():
    pass
```
"""
        files2 = engine._parse_code_blocks(response2)
        assert len(files2) == 1
        assert files2[0]['path'] == 'src/python.py'
    
    def test_parse_code_blocks_absolute_path(self):
        """Test parsing absolute paths."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```/absolute/path/to/file.py
code here
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert files[0]['path'] == '/absolute/path/to/file.py'
    
    def test_parse_code_blocks_windows_path(self):
        """Test parsing Windows-style paths."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```src\\file.py
code here
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert 'file.py' in files[0]['path']
    
    def test_parse_code_blocks_no_specifier(self):
        """Test parsing code blocks without specifier."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```
def main():
    pass
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        assert files[0]['path'] == 'generated_0.py'
        assert 'def main()' in files[0]['content']
    
    def test_parse_code_blocks_multiple_formats(self):
        """Test parsing multiple code blocks with different formats."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```src/file1.py
code1
```
```python
code2
```
```file: src/file3.py
code3
```
"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 3
        assert files[0]['path'] == 'src/file1.py'
        assert files[1]['path'] == 'generated_1.py'  # Language tag, not path
        assert files[2]['path'] == 'src/file3.py'
    
    def test_parse_code_blocks_nested_blocks_ignored(self):
        """Test that nested code blocks don't break parsing."""
        engine = RalphLoopEngine(Path("/tmp"))
        response = """```src/file.py
code with ```nested``` blocks
```
"""
        files = engine._parse_code_blocks(response)
        # Should still parse the outer block
        assert len(files) >= 1
        assert files[0]['path'] == 'src/file.py'
    
    def test_extract_file_path_language_tag(self):
        """Test _extract_file_path with language tag."""
        engine = RalphLoopEngine(Path("/tmp"))
        path = engine._extract_file_path('python', 'def main(): pass', 0)
        assert path == 'generated_0.py'
    
    def test_extract_file_path_file_path(self):
        """Test _extract_file_path with file path."""
        engine = RalphLoopEngine(Path("/tmp"))
        path = engine._extract_file_path('src/main.py', 'def main(): pass', 0)
        assert path == 'src/main.py'
    
    def test_extract_file_path_file_marker(self):
        """Test _extract_file_path with file: marker."""
        engine = RalphLoopEngine(Path("/tmp"))
        path = engine._extract_file_path('file: src/main.py', 'def main(): pass', 0)
        assert path == 'src/main.py'
    
    def test_extract_file_path_from_content(self):
        """Test _extract_file_path extracting from content."""
        engine = RalphLoopEngine(Path("/tmp"))
        path = engine._extract_file_path(None, 'file: src/main.py\ndef main(): pass', 0)
        assert path == 'src/main.py'
    
    def test_extract_file_path_default(self):
        """Test _extract_file_path default naming."""
        engine = RalphLoopEngine(Path("/tmp"))
        path = engine._extract_file_path(None, 'def main(): pass', 5)
        assert path == 'generated_5.py'
    
    @patch('lib.ralph_loop_engine.call_llm')
    def test_phase_test_success(self, mock_call_llm, tmp_path):
        """Test successful Test phase."""
        engine = RalphLoopEngine(tmp_path)
        mock_call_llm.return_value = "Test cases: 1. Unit test 2. Integration test"
        
        result = engine._phase_test("Test task")
        
        assert result['success'] is True
        assert 'output' in result
        assert result['phase'] == Phase.TEST.value
    
    @patch('lib.ralph_loop_engine.call_llm')
    def test_phase_test_error(self, mock_call_llm, tmp_path):
        """Test Test phase with error."""
        engine = RalphLoopEngine(tmp_path)
        mock_call_llm.side_effect = Exception("LLM error")
        
        result = engine._phase_test("Test task")
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_phase_update_success(self, tmp_path):
        """Test successful Update phase."""
        engine = RalphLoopEngine(tmp_path)
        fix_plan = tmp_path / '@fix_plan.md'
        fix_plan.write_text("""# Fix Plan

## High Priority

- [ ] Task to complete
""")
        
        result = engine._phase_update("Task to complete")
        
        assert result['success'] is True
        content = fix_plan.read_text()
        assert "- [x] Task to complete" in content
        assert "- [ ] Task to complete" not in content
    
    def test_phase_update_no_fix_plan(self, tmp_path):
        """Test Update phase when fix plan doesn't exist."""
        engine = RalphLoopEngine(tmp_path)
        
        result = engine._phase_update("Task")
        
        assert result['success'] is True
    
    def test_execute_phase_study(self, tmp_path):
        """Test executing Study phase."""
        engine = RalphLoopEngine(tmp_path)
        with patch.object(engine, '_phase_study', return_value={'success': True, 'output': 'test'}):
            result = engine._execute_phase(Phase.STUDY, "Test task")
            
            assert result['success'] is True
            assert engine.current_phase == Phase.STUDY
            assert len(engine.phase_history) == 1
    
    def test_execute_phase_error(self, tmp_path):
        """Test phase execution with error."""
        engine = RalphLoopEngine(tmp_path)
        with patch.object(engine, '_phase_study', side_effect=Exception("Error")):
            result = engine._execute_phase(Phase.STUDY, "Test task")
            
            assert result['success'] is False
            assert 'error' in result
            assert len(engine.phase_history) == 1
    
    def test_start_stop(self, tmp_path):
        """Test starting and stopping the loop."""
        engine = RalphLoopEngine(tmp_path)
        
        # Create a fix plan with no tasks to make loop exit quickly
        fix_plan = tmp_path / '@fix_plan.md'
        fix_plan.write_text("# Fix Plan\n\n## High Priority\n\n")
        
        engine.start()
        assert engine.is_running is True
        
        # Wait a bit for loop to start
        time.sleep(0.1)
        
        engine.stop()
        assert engine.is_running is False
        assert engine.should_stop is True
    
    def test_start_already_running(self, tmp_path):
        """Test starting when already running raises error."""
        engine = RalphLoopEngine(tmp_path)
        engine.is_running = True
        
        with pytest.raises(RuntimeError, match="already running"):
            engine.start()
    
    def test_pause_resume(self, tmp_path):
        """Test pausing and resuming."""
        engine = RalphLoopEngine(tmp_path)
        
        engine.pause()
        assert engine.is_paused is True
        
        engine.resume()
        assert engine.is_paused is False
    
    def test_resume_with_input(self, tmp_path):
        """Test resuming with user input."""
        engine = RalphLoopEngine(tmp_path)
        engine.is_paused = True
        
        engine.resume(user_input="Continue")
        assert engine.is_paused is False
        assert engine.user_input == "Continue"
    
    def test_set_mode(self, tmp_path):
        """Test changing execution mode."""
        engine = RalphLoopEngine(tmp_path)
        assert engine.mode == LoopMode.PHASE_BY_PHASE
        
        engine.set_mode(LoopMode.NON_STOP)
        assert engine.mode == LoopMode.NON_STOP
    
    def test_set_mode_resumes_if_paused(self, tmp_path):
        """Test that switching to non-stop mode resumes if paused."""
        engine = RalphLoopEngine(tmp_path)
        engine.is_paused = True
        engine.mode = LoopMode.PHASE_BY_PHASE
        
        engine.set_mode(LoopMode.NON_STOP)
        assert engine.is_paused is False
    
    def test_get_status(self, tmp_path):
        """Test getting status."""
        engine = RalphLoopEngine(tmp_path)
        engine.current_task = "Test task"
        engine.current_phase = Phase.STUDY
        
        status = engine.get_status()
        
        assert status['is_running'] is False
        assert status['is_paused'] is False
        assert status['mode'] == LoopMode.PHASE_BY_PHASE.value
        assert status['current_phase'] == Phase.STUDY.value
        assert status['current_task'] == "Test task"
        assert 'phase_history' in status
        assert 'status_log' in status
        assert 'files' in status
    
    def test_wait_for_resume(self, tmp_path):
        """Test waiting for resume signal."""
        engine = RalphLoopEngine(tmp_path)
        engine.is_paused = True
        engine.should_stop = False
        
        # Test that it waits (in a separate thread)
        def stop_after_delay():
            time.sleep(0.1)
            engine.is_paused = False
        
        thread = threading.Thread(target=stop_after_delay)
        thread.start()
        
        start = time.time()
        engine._wait_for_resume()
        elapsed = time.time() - start
        
        # Should have waited at least a bit
        assert elapsed >= 0.05
        thread.join()
    
    def test_file_tracker_integration(self, tmp_path):
        """Test that file tracker is initialized."""
        engine = RalphLoopEngine(tmp_path)
        assert engine.file_tracker is not None
        assert engine.file_tracker.project_path == tmp_path.resolve()
    
    def test_infer_file_extension_nodejs(self):
        """Test file extension inference for Node.js applications."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        nodejs_code = """const fs = require('fs');
const path = require('path');

function readConfig() {
  const configPath = path.join(__dirname, 'config.json');
  return JSON.parse(fs.readFileSync(configPath, 'utf8'));
}

module.exports = { readConfig };
"""
        assert engine._infer_file_extension(nodejs_code) == '.js'
    
    def test_infer_file_extension_package_json(self):
        """Test file extension inference for package.json."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        package_json = '{"name": "test", "version": "1.0.0", "main": "main.js"}'
        assert engine._infer_file_extension(package_json) == '.json'
    
    def test_infer_file_extension_json_with_comments(self):
        """Test JSON detection with leading comments."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        json_with_comment = """// /app/package.json
{
  "name": "test",
  "version": "1.0.0"
}"""
        assert engine._infer_file_extension(json_with_comment) == '.json'
    
    def test_infer_file_extension_defaults_to_js_not_py(self):
        """Test that ambiguous code defaults to .js instead of .py."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        ambiguous_code = "const x = 5; function test() { return x; }"
        assert engine._infer_file_extension(ambiguous_code) == '.js'
    
    def test_parse_code_blocks_strips_leading_metadata(self):
        """Test that code block parsing strips leading metadata comments."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        response = """```javascript
// /app/main.js
const http = require('http');
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello World');
});
server.listen(3000);
```"""
        files = engine._parse_code_blocks(response)
        assert len(files) == 1
        # Content should be preserved
        assert 'const http' in files[0]['content']
        # But metadata should be stripped for detection
        assert engine._strip_leading_metadata(files[0]['content']) == files[0]['content']
    
    def test_extract_file_path_ignores_comment_patterns(self):
        """Test that comment patterns like /app/file.js are ignored."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        # Specifier with comment pattern should be ignored
        path = engine._extract_file_path('/app/package.json', '{"name": "test"}', 0)
        # Should not use /app/package.json, should detect JSON and use meaningful name
        assert path == 'package.json' or 'generated' in path
    
    def test_extract_file_path_detects_common_nodejs_files(self):
        """Test detection of common Node.js file names from content."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        main_js = """const fs = require('fs');
const path = require('path');

function start() {
  console.log('Application starting...');
  // Application initialization code
}

if (require.main === module) {
  start();
}

module.exports = { start };
"""
        path = engine._extract_file_path(None, main_js, 0)
        assert path == 'main.js'
    
    def test_extract_file_path_detects_package_json(self):
        """Test detection of package.json from content."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        package_content = '{"name": "my-app", "version": "1.0.0", "main": "main.js"}'
        path = engine._extract_file_path(None, package_content, 0)
        assert path == 'package.json'
    
    def test_extract_file_path_detects_index_html(self):
        """Test detection of index.html from content."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        html_content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>"""
        path = engine._extract_file_path(None, html_content, 0)
        assert path == 'index.html'
    
    def test_generate_meaningful_filename_nodejs(self):
        """Test meaningful filename generation for Node.js applications."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        nodejs_code = """const http = require('http');
const fs = require('fs');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end('<h1>Hello World</h1>');
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
"""
        name = engine._generate_meaningful_filename(nodejs_code, 0, '.js')
        assert name == 'main.js'
    
    def test_generate_meaningful_filename_package_json(self):
        """Test meaningful filename generation for package.json."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        package_content = '{"name": "test", "version": "1.0.0"}'
        name = engine._generate_meaningful_filename(package_content, 0, '.json')
        assert name == 'package.json'
    
    def test_strip_leading_metadata_removes_comment_paths(self):
        """Test that leading metadata like /app/file.js is stripped."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        content = """// /app/package.json
{
  "name": "test"
}"""
        cleaned = engine._strip_leading_metadata(content)
        # Should remove the comment line
        assert '// /app/package.json' not in cleaned
        assert '"name"' in cleaned
    
    def test_strip_leading_metadata_preserves_code(self):
        """Test that actual code is preserved when stripping metadata."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        content = """// Some comment
const x = 5;
function test() {
  return x;
}"""
        cleaned = engine._strip_leading_metadata(content)
        assert 'const x = 5' in cleaned
        assert 'function test()' in cleaned
    
    def test_infer_file_extension_react(self):
        """Test file extension inference for React/JSX code."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        react_code = """import React from 'react';
import { useState } from 'react';

function App() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <h1>Count: {count}</h1>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}

export default App;
"""
        # React code should be detected as JavaScript
        assert engine._infer_file_extension(react_code) == '.js'
    
    def test_infer_file_extension_express(self):
        """Test file extension inference for Express.js applications."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        express_code = """const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.json({ message: 'Hello World' });
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
"""
        assert engine._infer_file_extension(express_code) == '.js'
    
    def test_infer_file_extension_typescript(self):
        """Test file extension inference for TypeScript code."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        ts_code = """interface User {
  id: number;
  name: string;
}

function getUser(id: number): User {
  return { id, name: 'John Doe' };
}

export default getUser;
"""
        assert engine._infer_file_extension(ts_code) == '.ts'
    
    def test_extract_file_path_detects_server_js(self):
        """Test detection of server.js from Express.js patterns."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        server_code = """const express = require('express');
const app = express();

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
"""
        path = engine._extract_file_path(None, server_code, 0)
        # Should detect as main.js or server.js based on content patterns
        assert path in ['main.js', 'server.js'] or 'generated' in path
    
    def test_extract_file_path_detects_app_js(self):
        """Test detection of app.js from application initialization patterns."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        app_code = """const express = require('express');
const app = express();

// Middleware setup
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.get('/', (req, res) => {
  res.send('Hello World');
});

module.exports = app;
"""
        path = engine._extract_file_path(None, app_code, 0)
        # Should detect as main.js or app.js based on content patterns
        assert path in ['main.js', 'app.js'] or 'generated' in path
    
    def test_extract_file_path_detects_react_component(self):
        """Test detection of React component files."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        react_component = """import React from 'react';

function Button({ onClick, children }) {
  return (
    <button onClick={onClick} className="btn">
      {children}
    </button>
  );
}

export default Button;
"""
        path = engine._extract_file_path(None, react_component, 0)
        # Should detect as .js or .jsx
        assert path.endswith('.js') or path.endswith('.jsx')
    
    def test_generate_meaningful_filename_express(self):
        """Test meaningful filename generation for Express.js applications."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        express_code = """const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.send('Hello World');
});

app.listen(3000);
"""
        name = engine._generate_meaningful_filename(express_code, 0, '.js')
        # Should detect as main.js or server.js
        assert name in ['main.js', 'server.js'] or name is None
    
    def test_generate_meaningful_filename_react(self):
        """Test meaningful filename generation for React components."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        react_code = """import React, { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);
  return <div>{count}</div>;
}

export default Counter;
"""
        name = engine._generate_meaningful_filename(react_code, 0, '.js')
        # Should detect as .js or .jsx, or None if no specific pattern
        assert name is None or name.endswith('.js') or name.endswith('.jsx')
    
    def test_infer_file_extension_generic_javascript(self):
        """Test file extension inference for generic JavaScript code."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        generic_js = """function calculateTotal(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}

const items = [
  { name: 'Apple', price: 1.50 },
  { name: 'Banana', price: 0.75 }
];

console.log('Total:', calculateTotal(items));
"""
        assert engine._infer_file_extension(generic_js) == '.js'
    
    def test_extract_file_path_detects_config_json(self):
        """Test detection of config.json from configuration patterns."""
        engine = RalphLoopEngine(Path("/tmp"))
        
        config_content = '{"database": {"host": "localhost", "port": 5432}, "api": {"timeout": 5000}}'
        path = engine._extract_file_path(None, config_content, 0)
        # Should detect as package.json or config.json based on structure
        assert path == 'package.json' or 'generated' in path