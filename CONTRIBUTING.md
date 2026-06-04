# Contributing to Guimauve

Thank you for your interest in our project. 

> ⚠️ **Important Notice:** This repository is primarily maintained by **SII** to facilitate collaboration and deployment with our clients. **We do not accept unsolicited external Pull Requests.** If you are an external developer and wish to propose changes, please open an issue first to discuss it with us.

---

## Reporting Issues & Feature Requests

Whether you are a client or an external user, you can help us improve by reporting bugs or suggesting features. Please use our templates:

* **Bug Report:** Something is broken or behaves unexpectedly.
* **Feature Request:** You want to see a new capability added.

*Please fill out the templates completely.*

---

## Internal Development Guidelines

*This section applies exclusively to **SII** team members and authorized contributors.*

### 1. Branching Strategy

| Branch Pattern | Purpose | Target PR |
| :--- | :--- | :--- |
| `main` | Production-ready, stable code. | *Never commit directly* |
| `feat/<issue-id>-<name>` | New features or enhancements. | `main` |
| `fix/<issue-id>-<name>` | Bug fixes. | `main` |
| `docs/<name>` | Major documentation changes. | `main` |
| `chore/<name>` | Maintenance, CI/CD, updates, tests. | `main` |

*Note: If no GitHub issue exists for your changes, simply omit the `<issue-id>-` prefix.*
### 2. Commit Messages

We strictly enforce the [Conventional Commits](https://www.conventionalcommits.org/) specification. 

**Format:** `<type>(<scope>): <description>`

* `feat`: A new feature
* `fix`: A bug fix 
* `chore`: Routine tasks, dependency updates, no production code change.
* `docs`: Documentation changes only.