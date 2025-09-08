# Parallel Task Execution with Claude Code

Claude Code supports several methods for running tasks in parallel, significantly improving performance for complex workflows.

## 1. Multiple Tool Calls in Single Message

The most common parallel execution pattern is including multiple tool calls in one response:

### Example: Git Operations
```
# Claude executes these simultaneously:
- git status
- git diff
- git log --oneline -10
```

### Example: File Operations
```
# Reading multiple files in parallel:
- Read package.json
- Read tsconfig.json
- Read README.md
```

### Example: Search Operations
```
# Multiple searches run concurrently:
- Grep for "TODO" in *.ts files
- Grep for "FIXME" in *.js files
- Glob for test files **/*test*
```

## 2. Background Bash Commands

Use `run_in_background=True` for long-running processes:

### Starting Background Processes
```bash
# Start development server
Bash(command="npm run dev", run_in_background=True)

# Start database
Bash(command="docker-compose up postgres", run_in_background=True)

# Run tests
Bash(command="pytest --watch", run_in_background=True)
```

### Monitoring Background Output
```bash
# Check output from background processes
BashOutput(bash_id="shell_123")

# Filter output with regex
BashOutput(bash_id="shell_123", filter="ERROR|WARN")
```

### Managing Background Processes
```bash
# List all background shells
/bashes

# Kill a specific background process
KillBash(shell_id="shell_123")
```

## 3. Concurrent Task Agents

Launch multiple specialized agents for independent work:

### Multiple General Purpose Agents
```
Task(subagent_type="general-purpose", prompt="Search codebase for authentication logic")
Task(subagent_type="general-purpose", prompt="Find all database migration files")
Task(subagent_type="general-purpose", prompt="Analyze error handling patterns")
```

### Mixed Agent Types
```
Task(subagent_type="dspy-expert-architect", prompt="Review DSPy pipeline optimization")
Task(subagent_type="general-purpose", prompt="Update documentation")
```

## 4. Batch File Operations

Claude automatically batches related operations:

### Reading Multiple Configuration Files
```
# All executed in parallel:
Read(.env)
Read(package.json)
Read(docker-compose.yml)
Read(requirements.txt)
```

### Multiple Search Patterns
```
# Concurrent searches:
Grep(pattern="class.*Exception", glob="**/*.py")
Grep(pattern="async def", glob="**/*.py") 
Grep(pattern="TODO|FIXME", glob="**/*")
```

### Multiple Glob Patterns
```
# Find different file types simultaneously:
Glob(pattern="**/*.test.ts")
Glob(pattern="**/*.spec.js")
Glob(pattern="**/mock*.py")
```

## 5. Real-World Examples

### Code Review Workflow
```
# Parallel code analysis:
- git status
- git diff --stat
- Grep for "console.log" in modified files
- Grep for "TODO" in modified files
- Read all modified files
```

### Testing and Building
```
# Start multiple processes:
Bash("npm run test", run_in_background=True)
Bash("npm run lint", run_in_background=True) 
Bash("npm run typecheck", run_in_background=True)

# Monitor all processes:
BashOutput(bash_id="test_shell")
BashOutput(bash_id="lint_shell")
BashOutput(bash_id="typecheck_shell")
```

### Codebase Analysis
```
# Launch multiple research agents:
Task("Find all API endpoints")
Task("Map database schema")
Task("Identify security patterns")
Task("Document configuration options")
```

## 6. Best Practices

### Maximize Parallelization
- **Batch independent operations** in single messages
- **Use background processes** for long-running tasks
- **Launch multiple agents** for separate research tasks

### Resource Management
- **Monitor background processes** regularly
- **Kill unused processes** to free resources
- **Use appropriate timeouts** for Bash commands

### Error Handling
- **Check all parallel operations** complete successfully
- **Have fallback strategies** for failed parallel tasks
- **Use filtered output** to focus on relevant information

### Performance Tips
- **Combine related searches** in single messages
- **Use specific glob patterns** to reduce search scope
- **Filter background output** to reduce noise

## 7. Common Patterns

### Development Server + File Watching
```bash
# Start dev server in background
Bash("npm run dev", run_in_background=True)

# Watch for file changes and run tests
Bash("npm run test:watch", run_in_background=True)

# Monitor both processes
BashOutput(bash_id="dev_server", filter="Error|Warning")
BashOutput(bash_id="test_runner", filter="FAIL|PASS")
```

### Multi-Stage Build Pipeline
```bash
# Run build stages in parallel where possible
Bash("npm run build:client", run_in_background=True)
Bash("npm run build:server", run_in_background=True)

# Then combine results
BashOutput(bash_id="client_build")
BashOutput(bash_id="server_build")
```

### Comprehensive Codebase Search
```
# Multiple search strategies:
Task("Search for authentication patterns")
Task("Find all database queries") 
Task("Locate error handling code")
Task("Map API endpoints")

# While also doing direct searches:
Grep("login|auth", glob="**/*.ts")
Grep("SELECT|INSERT|UPDATE", glob="**/*.sql")
Grep("try.*catch|except", glob="**/*")
```

## 8. Limitations and Considerations

### Not Truly Parallel
- Tool calls in same message run concurrently but within Claude's processing
- Background Bash is truly parallel system processes

### Resource Limits  
- Don't exceed system CPU/memory limits
- Background processes consume system resources

### Dependency Management
- Ensure parallel tasks don't conflict
- Some operations must be sequential (e.g., setup before tests)

### Output Management
- Parallel output can be overwhelming
- Use filtering and selective monitoring

## Summary

Claude Code's parallel capabilities significantly improve workflow efficiency through:

1. **Multiple tool calls** per message for concurrent operations
2. **Background processes** for long-running tasks  
3. **Multiple task agents** for independent research/work
4. **Automatic batching** of related operations

Use these patterns to maximize productivity and minimize wait times in your development workflows.