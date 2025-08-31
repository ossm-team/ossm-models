# OSSM Models

`ossm-models` implements the **Sensorimotor Modeling Standard (SMS)** and aims to provide a collection of standardized, reusable models for goal-driven sensorimotor neuroscience.
It is one of the core packages of the [OSSM ecosystem](https://github.com/ossm-team), supported by the [NWO Open Science Fund][nwo]https://www.nwo.nl/en/news/open-science-fund-2023-grants-awarded.

---

## Vision

This package is part of a broader effort to build an **open, community-driven ecosystem** for computational sensorimotor neuroscience.
By standardizing models, tasks, and analyses, OSSM ensures that models are **interoperable, reusable, and comparable** across labs and projects.
The long-term goal is to launch a unified research paradigm where models, benchmarks, and metrics are openly shared and continuously expanded.

---

## Features

- **Schema-driven**: All models are validated against the [`SMS.xsd`](./SMS.xsd) schema.
- **Typed core**: Shared data types, model objects, and XML parsers live under `ossm_models/core/`.
- **Examples**: See [`examples/sample_fpn.xml`](./examples/sample_fpn.xml) for a reference model.
- **Extensible**: Add new models while reusing the shared infrastructure.

---

## Install

Requires **Python 3.11+**.

```bash
pip install -e .
```

---

## Quickstart

Consult the [examples](./examples/) directory for reference models. Detailed usage will be documented in the future.

---

## Related Packages

- [`ossm-base`](https://github.com/ossm-team/ossm-base) – shared types and utilities
- [`ossm-tasks`](https://github.com/ossm-team/ossm-tasks) – task catalogue & STEF standard
- [`ossm-analysis`](https://github.com/ossm-team/ossm-analysis) – analysis methods & benchmarks

---

## Contribution

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

GPL-3.0. See [LICENSE](./LICENSE).

---
