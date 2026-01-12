# Ralph Personas Catalog

> Comprehensive catalog of personas available within the Ralph autonomous development workflow

---

## Overview

This catalog documents all personas available within the Ralph workflow system. Personas are specialized roles that provide focused capabilities within the autonomous development loop.

**Persona Categories:**
- **Tier 1**: Ralph-integrated personas (high priority, workflow-integrated)
- **Tier 2**: Standalone personas (medium priority, on-demand)
- **Tier 3**: Specialized personas (lower priority, niche needs)

---

## Tier 1: Ralph-Integrated Personas

These personas integrate directly with the Ralph workflow system, following the same pattern and status reporting as the core workflow.

### 1. Product Owner (`ralph-product-owner.mdc`)

**Priority:** 1.5  
**Status:** ✅ Active

**Purpose:** Product strategy and requirements management

**Capabilities:**
- Define product strategy and business goals
- Prioritize work by business value and user impact
- Create and update specifications
- Validate alignment with business goals
- Communicate decisions and trade-offs

**When to Use:**
- Product strategy work needed
- Requirements definition
- Prioritization decisions
- Specification creation/updates

**Integration:**
- Reads `specs/` files for requirements
- Updates `@fix_plan.md` with priorities
- Outputs to `specs/prd.json` and specification files

---

### 2. QA/Testing (`ralph-qa.mdc`)

**Priority:** 1.6  
**Status:** ✅ Active

**Purpose:** Quality assurance, test creation, bug detection

**Capabilities:**
- Write comprehensive tests for implemented features
- Validate functionality and acceptance criteria
- Detect bugs before deployment
- Test edge cases and error conditions
- Maintain test coverage and documentation

**When to Use:**
- Tests need to be written for features
- Acceptance criteria need validation
- Bug detection or quality assurance is needed
- Test coverage needs improvement

**Integration:**
- Reads `specs/prd.json` for acceptance criteria
- Creates test files in project directories
- Validates implementations from Ralph's "Implement" step

---

### 3. Code Reviewer (`ralph-reviewer.mdc`)

**Priority:** 1.7  
**Status:** ✅ Active

**Purpose:** Code quality, best practices, refactoring guidance

**Capabilities:**
- Review code for quality and consistency
- Validate architecture and design patterns
- Identify refactoring opportunities
- Ensure adherence to coding standards
- Provide constructive feedback

**When to Use:**
- Code review needed
- Code quality validation required
- Architecture validation needed
- Refactoring opportunities need identification
- Code quality standards need enforcement

**Integration:**
- Reviews code from Ralph's "Implement" step
- Provides feedback before completion
- Validates code meets quality standards

---

### 4. Technical Writer (`ralph-docs.mdc`)

**Priority:** 1.8  
**Status:** ✅ Active

**Purpose:** Documentation creation and maintenance

**Capabilities:**
- Write technical documentation
- Create API reference documentation
- Maintain README files
- Write user guides and tutorials
- Document architectural decisions

**When to Use:**
- Documentation needs to be created or updated
- API documentation is needed
- User guides need to be written
- Documentation needs improvement or maintenance

**Integration:**
- Reads code changes and `@fix_plan.md` for documentation tasks
- Creates and updates documentation files
- Ensures documentation matches implementation

---

### 5. DevOps/Infrastructure (`ralph-devops.mdc`)

**Priority:** 1.9  
**Status:** ✅ Active

**Purpose:** CI/CD, deployment, infrastructure management

**Capabilities:**
- Configure CI/CD pipelines
- Manage deployment configurations
- Handle infrastructure setup
- Monitor deployment health
- Ensure reliable deployment and operations

**When to Use:**
- CI/CD pipelines need configuration
- Deployment setup is needed
- Infrastructure configuration is required
- Deployment or infrastructure issues need resolution

**Integration:**
- Reads `@fix_plan.md` for deployment and infrastructure tasks
- Configures CI/CD and infrastructure files
- Validates deployment readiness

---

## Tier 2: Standalone Personas (Planned)

These personas provide specialized capabilities but don't require full Ralph workflow integration. They can be invoked on-demand for specific needs.

### 6. UX/Design Persona

**Status:** 📋 Planned

**Purpose:** User experience design, UI/UX guidance

**Capabilities:**
- Review user experience designs
- Provide UX recommendations
- Validate design decisions
- Suggest UI improvements
- Ensure design system consistency

**When to Use:**
- UX/design work is needed
- User experience validation required
- Design improvements needed
- Design system consistency needed

---

### 7. Security Auditor Persona

**Status:** 📋 Planned

**Purpose:** Security reviews, vulnerability assessment

**Capabilities:**
- Security code reviews
- Vulnerability assessments
- Security best practice validation
- Security recommendations
- Dependency security audits

**When to Use:**
- Security reviews needed
- Security concerns arise
- Vulnerability assessment needed
- Security best practices need validation

---

### 8. Performance Engineer Persona

**Status:** 📋 Planned

**Purpose:** Performance optimization, profiling, monitoring

**Capabilities:**
- Performance profiling
- Optimization recommendations
- Performance testing
- Monitoring setup
- Performance metrics analysis

**When to Use:**
- Performance issues detected
- Optimization needed
- Performance testing required
- Performance monitoring needed

---

### 9. Accessibility Specialist Persona

**Status:** 📋 Planned

**Purpose:** Accessibility compliance (A11y), inclusive design

**Capabilities:**
- Accessibility audits
- WCAG compliance validation
- Accessibility testing
- Inclusive design recommendations
- Assistive technology testing

**When to Use:**
- Accessibility reviews needed
- A11y work required
- WCAG compliance validation needed
- Inclusive design improvements needed

---

### 10. Research/Architecture Persona

**Status:** 📋 Planned

**Purpose:** Technical research, system design, architecture decisions

**Capabilities:**
- Technical research
- Architecture design
- Technology evaluation
- System design recommendations
- Feasibility studies

**When to Use:**
- Architecture decisions needed
- Technical research required
- Technology evaluation needed
- System design recommendations needed

---

## Tier 3: Specialized Personas (Planned)

These personas provide niche capabilities for specific project needs.

### 11. SEO Specialist Persona

**Status:** 📋 Planned

**Purpose:** SEO optimization, content strategy

**Capabilities:**
- Optimize landing pages for SEO
- Provide SEO recommendations
- Create SEO content strategies
- Validate SEO implementations

**When to Use:**
- SEO optimization needed (relevant for `landings/` and `suno-seo/` project)
- SEO content strategy needed
- SEO validation required

---

### 12. Prompt Engineer Persona

**Status:** 📋 Planned

**Purpose:** Prompt engineering, prompt optimization

**Capabilities:**
- Optimize prompts for AI systems
- Create prompt templates
- Validate prompt effectiveness
- Provide prompt engineering guidance

**When to Use:**
- Prompt optimization needed (highly relevant for SELF framework)
- Prompt templates needed
- Prompt engineering guidance required

---

## Usage Guidelines

### Activating Personas

**Ralph-Integrated Personas (Tier 1):**
- Automatically integrated with Ralph workflow
- Activate by requesting persona-specific work
- Example: "Let QA write tests for this feature"
- Example: "Product Owner should prioritize the backlog"

**Standalone Personas (Tier 2 & 3):**
- Invoked on-demand for specific needs
- Example: "Security Auditor should review this code"
- Example: "Performance Engineer should optimize this"

### Persona Selection

Choose personas based on:
1. **Work type**: What kind of work is needed?
2. **Integration needs**: Does it need workflow integration?
3. **Specialization**: What specific expertise is needed?
4. **Priority**: How urgent is the work?

### Persona Workflow

For Ralph-integrated personas:
1. Persona activates based on request or context
2. Follows Ralph workflow steps
3. Integrates with `@fix_plan.md` and `specs/`
4. Outputs RALPH_STATUS blocks
5. Coordinates with other personas as needed

---

## Persona Comparison

| Persona | Priority | Integration | Focus | Output |
|---------|----------|-------------|-------|--------|
| Product Owner | 1.5 | Ralph | Strategy & Requirements | Specs & Priorities |
| QA/Testing | 1.6 | Ralph | Quality & Testing | Tests & Bug Reports |
| Code Reviewer | 1.7 | Ralph | Code Quality | Review Feedback |
| Technical Writer | 1.8 | Ralph | Documentation | Documentation Files |
| DevOps | 1.9 | Ralph | Deployment | CI/CD & Infrastructure |
| UX/Design | N/A | Standalone | User Experience | Design Guidance |
| Security | N/A | Standalone | Security | Security Reviews |
| Performance | N/A | Standalone | Performance | Optimization |
| Accessibility | N/A | Standalone | A11y | Accessibility Reviews |
| Research | N/A | Standalone | Architecture | Research & Design |
| SEO | N/A | Standalone | SEO | SEO Strategy |
| Prompt Engineer | N/A | Standalone | Prompts | Prompt Optimization |

---

## Integration Patterns

### Persona Chain Pattern

Personas can work together in sequences:
1. **Product Owner** → Defines requirements
2. **Developer Ralph** → Implements feature
3. **QA** → Writes tests
4. **Code Reviewer** → Reviews code
5. **Technical Writer** → Documents feature
6. **DevOps** → Deploys feature

### Persona Parallel Pattern

Personas can work in parallel:
- **Code Reviewer** and **QA** can review different aspects simultaneously
- **Technical Writer** can document while **DevOps** configures deployment

### Persona Feedback Loop

Personas provide feedback loops:
- **QA** tests inform **Developer Ralph** fixes
- **Code Reviewer** feedback guides **Developer Ralph** improvements
- **Product Owner** validates **Developer Ralph** implementations

---

## Status Reporting

All Ralph-integrated personas follow the same status reporting format:

```
---RALPH_STATUS---
STATUS: IN_PROGRESS | COMPLETE | BLOCKED
TASKS_COMPLETED_THIS_LOOP: <number>
FILES_MODIFIED: <number>
TESTS_STATUS: PASSING | FAILING | NOT_RUN
WORK_TYPE: <persona-specific work type>
EXIT_SIGNAL: false | true
RECOMMENDATION: <one line summary>
---END_RALPH_STATUS---
```

**Work Types by Persona:**
- Product Owner: `PRODUCT_STRATEGY`, `REQUIREMENTS`, `PRIORITIZATION`
- QA: `TESTING`, `DEBUGGING`
- Code Reviewer: `REVIEW`, `REFACTORING`
- Technical Writer: `DOCUMENTATION`
- DevOps: `INFRASTRUCTURE`, `DEPLOYMENT`

---

## File Structure

Personas work with these file structures:

```
.cursor/rules/
├── ralph-core.mdc              # Priority 1: Core workflow
├── ralph-product-owner.mdc     # Priority 1.5: Product Owner
├── ralph-qa.mdc                # Priority 1.6: QA/Testing
├── ralph-reviewer.mdc          # Priority 1.7: Code Reviewer
├── ralph-docs.mdc              # Priority 1.8: Technical Writer
├── ralph-devops.mdc            # Priority 1.9: DevOps/Infrastructure
├── ralph-status.mdc            # Priority 2: Status reporting
├── ralph-rate-limits.mdc       # Priority 3: Rate limit handling
├── ralph-completion.mdc        # Priority 4: Completion detection
├── ralph-priorities.mdc        # Priority 5: Task prioritization
└── PERSONAS.md                 # This catalog
```

---

## Future Enhancements

### Planned Improvements

1. **Persona activation patterns**: Improve automatic persona activation
2. **Persona coordination**: Better coordination between personas
3. **Persona metrics**: Track persona effectiveness
4. **Standalone persona integration**: Better integration for standalone personas

### Potential New Personas

- **Design System Manager**: Maintains design systems and component libraries
- **API Designer**: Designs and documents APIs
- **Data Engineer**: Handles data pipelines and data architecture
- **Site Reliability Engineer (SRE)**: Focuses on reliability and operations

---

**Version:** 1.0.0  
**Last Updated:** 2026-01-09  
**Status:** Active

---

_For more information, see `.cursor/rules/README.md` for workflow documentation._