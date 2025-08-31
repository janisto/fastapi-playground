---
mode: 'agent'
description: 'Update README.md Documentation'
---
# Task: Update README.md Documentation

You are tasked with reviewing and updating the README.md file for this repository. This file provides guidance to VS Code Copilot when working with code in this repository.

## Your Mission

Conduct a comprehensive analysis of the entire codebase and update the README.md file to ensure it is 100% accurate, complete, and helpful for future VS Code Copilot interactions.

## Analysis Requirements

### 1. Project Overview Verification
- Verify the project description is accurate
- Check if the stated purpose aligns with actual implementation
- Identify any missing key features or capabilities

### 2. Tech Stack Analysis
- Verify all frameworks and their versions by checking:
  - pyproject.toml for dependencies
  - uv.lock for exact versions
  - Any configuration files
- Identify any technologies used but not documented
- Remove any technologies listed but not actually used
- Check on correctness of folder references (e.g., app/ etc.)

### 3. Commands Verification
- Test and verify all commands in Justfile
- Document any additional useful commands
- Ensure command descriptions are accurate
- Add any missing commonly-used commands

### 4. Architecture & Directory Structure
- Scan the entire directory structure using recursive listing
- Verify all documented paths exist
- Document any significant directories or files not mentioned
- Check routing structure against actual Open API docs
- Verify content collections configuration
- Document actual file naming conventions and patterns

### 5. Automation
- Identify any GitHub Actions workflows
- Document any build or deployment scripts

### 6. Configuration Files
- Document all configuration files and their purposes:
  - .env variables (document required vars, not values)
  - Any other config files

### 7. Development Guidelines
- Extract any coding conventions from existing code
- Document file naming patterns
- Identify comment patterns or documentation standards
- Note any apparent best practices

### 8. Integration Points
- Document any external services or APIs used
- Identify environment variables needed
- Document any webhooks or external dependencies

## Output Requirements

Create an updated README.md file that:

1. **Maintains the current structure** but updates all content for accuracy
2. **Adds new sections** for any significant findings not currently documented
3. **Removes outdated information** that no longer applies
4. **Uses clear, concise language** appropriate for AI assistance
5. **Includes specific examples** where helpful
6. **Prioritizes information** most useful for code modifications and development

## Important Notes

- Be thorough but concise - every line should provide value
- Focus on information that helps VS Code Copilot understand how to work with the codebase
- Include any "gotchas" or non-obvious aspects of the project
- Document both what exists AND how it should be used
- If you find discrepancies between documentation and reality, always favor reality

## Process

1. First, analyze the entire codebase systematically
2. Compare your findings with the current README.md
3. Create an updated version that reflects the true state of the project
4. Ensure all paths, commands, and technical details are verified and accurate

Remember: The goal is to create documentation that allows VS Code Copilot to work effectively with this codebase without confusion or errors.
