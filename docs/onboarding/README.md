# KiCad Onboarding

Welcome to the Electrical team's KiCad onboarding. This replaces the Altium onboarding: Reality Labs
boards are designed in KiCad 10, with one shared parts library that every project carries as a git
submodule. By the end you will have set up KiCad with that library, made a real part (symbol,
footprint, 3D model), submitted it to the library as a pull request, and placed it on a board.

**Time to complete:** 3 to 5 hours.

## Before you start

- Join the Discord server and open a thread in `#onboarding-posts`. Ask there when you get stuck.
- Ask a lead to add your GitHub account to the `uwrealitylabs` organization. You need it to push a branch.
- Install Git. Install KiCad 10. Document 1 walks through both.
- Have a terminal you are comfortable in (PowerShell, Terminal.app, or any Linux shell).

## Documents

1. [Setup: KiCad, Git and the library](01-setup.md)
2. [Finding parts before you make them](02-finding-parts.md)
3. [Making a symbol](03-making-a-symbol.md)
4. [Making a footprint and attaching the 3D model](04-making-a-footprint.md)
5. [Submitting the part as a pull request](05-submitting-a-part.md)
6. [Using the part on a board](06-using-the-part.md)

Documents 3 to 6 build one real part end to end: the AP2210K-3.3, a 300 mA LDO from Diodes in a
SOT-23-5 package. Follow along with that part first, then repeat the flow with a part your project needs.

## When you are done

Ping an EE lead (@Vincent Xie) in Discord `#onboarding-posts` with the link to your pull request.
We go through your symbol and footprint against the datasheet together, then you are on the team.

## Where things live

- Library: <https://github.com/uwrealitylabs/kicad-library> (symbols, footprints, 3D models, templates)
- Rules for parts and the review checklist: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Moving an older project onto this library layout: [MIGRATION.md](../../MIGRATION.md)
