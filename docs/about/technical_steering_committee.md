# Kedro's Technical Steering Committee

Kedro is a graduate-stage project within [LF AI & Data](https://lfaidata.foundation/).

The term "Technical Steering Committee" (TSC) describes the group of Kedro voting members, maintainers, and advisors. We list Kedro's [current](#current-tsc-members) and [past](#past-tsc-members) TSC members and maintainers on this page.

The TSC is responsible for the project's future development; you can read about our duties in our [Technical Charter](https://github.com/kedro-org/kedro/blob/main/kedro_technical_charter.pdf). We accept new members into the TSC to fuel Kedro's continued development.

On this page we describe:

- [Kedro TSC roles](#kedro-tsc-roles)
- [Responsibilities of a voting member](#responsibilities-of-a-voting-member)
- [Process to become a voting member](#process-to-become-a-voting-member)
- [Responsibilities of a maintainer](#responsibilities-of-a-maintainer)
- [Process to become a maintainer](#process-to-become-a-maintainer)
- [Responsibilities of an advisor](#responsibilities-of-an-advisor)
- [Process to become an advisor](#process-to-become-an-advisor)
- [Current TSC members](#current-tsc-members)
- [Past TSC members](#past-tsc-members)
- [Voting process](#voting-process)
- [Adding or removing TSC members](#adding-or-removing-tsc-members)

## Kedro TSC roles

The Kedro TSC is responsible for the project's future development. The TSC is made up of the following roles:

### Voting members

Voting Members form the core of the TSC and hold the right to vote on both code modifications and membership additions. They are expected to make significant contributions to the strategy, direction, and governance of the project. Their primary responsibility is to ensure the long-term success of Kedro.

### Maintainers

Maintainers have repository access and full participation rights in discussions but do not hold voting privileges. They are active contributors who focus on different areas of the project. Maintainers are responsible for maintaining the health of the project, participating in planning and (technical) design decisions, and otherwise acting as part of the core Kedro development team.

### Advisors

Advisors are individuals who are not actively contributing to the codebase or attending regular meetings but provide valuable expertise, feedback, and strategic guidance to the Kedro project.

## Responsibilities of a voting member

- Defining and maintaining the product vision and roadmap
- Supporting key technical and strategic initiatives
- Providing input on complex or high-impact technical decisions
- Advising and mentoring contributors
- Representing Kedro within the broader community
- Attend regular team meetings to discuss the project plans and roadmap

### Voting rights
Voting members take part in three types of votes:

- Membership additions – new voting members must receive majority approval (≥50%) from existing voting members (see more details below)
- Code modifications – follows the [KEP process](https://github.com/kedro-org/kedro/discussions/5150)
- Core dataset additions or removals – follows the [kedro-datasets contribution guide](https://github.com/kedro-org/kedro-plugins/blob/main/kedro-datasets/CONTRIBUTING.md)


## Process to become a voting member
Just contributing does not make you a voting member. You need to show commitment to Kedro's long-term success by working with existing TSC members for at least one year.

We look for people who can do at least some of the following:

- Steer the direction of the project to ensure it retains relevance, including by bringing awareness of industry trends to the team and connecting the project to complementary initiatives
- Give talks about the project at conferences and online events, write blog posts, or other forms of advocacy
- Show excitement about the future of Kedro

Any current voting member may nominate a new candidate and will serve as their advocate, responsible for initiating and managing the voting process. The nominating member should open a pull request and formally call for a vote on the candidate, posting the announcement in the #kedro-tsc channel on the Kedro Slack organisation.

The voting period should remain open for at least two weeks, and the proposal will pass with a majority approval. Once voting concludes, the #kedro-tsc channel should be updated with the final results.

### Inactivity and removal
Voting members may be automatically removed after 6 months of inactivity, without requiring a formal vote. Inactivity is defined as:

- Not participating in any votes for 6 consecutive months (if any votes were required)
- Not joining regular technical design meetings or roadmap discussions for more than 6 months

A former voting member may rejoin in the future, provided they secure an advocate among current voting members who will sponsor their nomination for a new vote.

## Responsibilities of a maintainer
Depending on the maintainer role in the team, they are responsible for some of the following:

- Driving implementation, technical quality, and code excellence
- Be proactive about project maintenance including security, updates, CI/CD, builds and infrastructure
- Leading work on user experience, interface design, and information architecture
- Improve the aesthetics and usability of the project, including its documentation, website, and user interfaces (graphical and textual)
- Conducting product research, gathering user feedback, and shaping feature priorities
- Give priority to the work following the product roadmap to move the project forward

### Community management

- Ensure that ongoing pull requests are moving forward at the right pace or closing them
- Guide the community to use our various communication channels:
    - [GitHub issues](https://github.com/kedro-org/kedro/issues) for feature requests and bug reports
    - [GitHub discussions](https://github.com/kedro-org/kedro/discussions) to discuss the future of the Kedro project
    - [Slack](https://slack.kedro.org) for questions and to support other users


## Process to become a maintainer
Any current voting member may nominate a new candidate and will serve as their advocate, responsible for initiating and managing the voting process. The nominating member should open a pull request and formally call for a vote on the candidate, posting the announcement in the #kedro-tsc channel on the Kedro Slack organisation.

The voting period should remain open for at least two weeks, and the proposal will pass with a majority approval. Once voting concludes, the #kedro-tsc channel should be updated with the final results.

The new maintainer should then be added to the `kedro-developers` team on the Kedro GitHub organisation,
the `kedro-tsc` channel on the Kedro Slack organisation, the regular TSC meetings, and the `CITATION.cff` file.

### Inactivity and removal
Maintainers who do not contribute code, documentation, or attend regular meetings for 6 months will be automatically removed from the [current TSC members](#current-tsc-members) list, `kedro-developers` team, and `CITATION.cff` file. They may be invited to join the [advisor](#advisors) role if they are interested in continuing to support and contribute to the project in a different capacity.


## Responsibilities of an advisor

- Providing ongoing, high-level guidance on direction, governance, and technical topics (rather than ad-hoc support)
- Acting as external ambassadors or thought partners
- Sharing lessons learned and best practices from adjacent domains

## Process to become an advisor
Any current voting member may nominate a new candidate and will serve as their advocate, responsible for initiating and managing the voting process. The nominating member should open a pull request and formally call for a vote on the candidate, posting the announcement in the #kedro-tsc channel on the Kedro Slack organisation.

The voting period should remain open for at least two weeks, and the proposal will pass with a majority approval. Once voting concludes, the #kedro-tsc channel should be updated with the final results.


### Inactivity and removal
Advisors may be automatically removed after 12 months of inactivity. Inactivity is defined as a lack of any engagement with Kedro during this period.


## Current TSC members

<!-- DO NOT EDIT THIS AND MERGE A PR WITHOUT A VOTE TO SIGN OFF ANY CHANGES -->

| Name                                                     | Organisation                                                                            |
|----------------------------------------------------------|---------------------------------------------------------------------------------------- |
| [Ankita Katiyar](https://github.com/ankatiyar)           | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Deepyaman Datta](https://github.com/deepyaman)          | [Dagster Labs](https://dagster.io)                                                      |
| [Dmitry Sorokin](https://github.com/DimedS)              | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Huong Nguyen](https://github.com/Huongg)                | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Ivan Danov](https://github.com/idanov)                  | [Palantir](https://www.palantir.com/)                                                   |
| [Jitendra Gundaniya](https://github.com/jitu5)           | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Joel Schwarzmann](https://github.com/datajoely)         | [Aneira Health](https://www.aneira.health)                                              |
| [Juan Luis Cano](https://github.com/astrojuanlu)         | [Canonical](https://www.canonical.com )                                                 |
| [Laura Couto](https://github.com/lrcouto)                | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Marcin Zabłocki](https://github.com/marrrcin)           | [Printify, Inc.](https://printify.com/)                                                 |
| [Merel Theisen](https://github.com/merelcht)             | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Nok Lam Chan](https://github.com/noklam)                | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Rashida Kanchwala](https://github.com/rashidakanchwala) | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Ravi Kumar Pilla](https://github.com/ravi-kumar-pilla)  | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Sajid Alam](https://github.com/SajidAlamQB)             | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Simon Brugman](https://github.com/sbrugman)             | [ING](https://www.ing.com/)                                                             |
| [Stephanie Kaiser](https://github.com/stephkaiser)       | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Tynan DeBold](https://github.com/tynandebold)           | [QuantumBlack, AI by McKinsey](https://www.mckinsey.com/capabilities/quantumblack)      |
| [Yetunde Dada](https://github.com/yetudada)              | [Astronomer](https://www.astronomer.io/)                                                |
| [Yolan Honoré-Rougé](https://github.com/Galileo-Galilei) | [Société Générale Assurances](https://www.assurances.societegenerale.com/en/individual) |


## Past TSC members

Kedro was originally designed by [Aris Valtazanos](https://github.com/arisvqb) and [Nikolaos Tsaousis](https://github.com/tsanikgr) at [QuantumBlack](https://www.mckinsey.com/capabilities/quantumblack) to solve challenges they faced in their project work. Their work was later turned into an internal product by [Peteris Erins](https://github.com/Pet3ris), [Ivan Danov](https://github.com/idanov), [Nikolaos Kaltsas](https://github.com/nikos-kal), [Meisam Emamjome](https://github.com/misamae) and [Nikolaos Tsaousis](https://github.com/tsanikgr).

Former core team members with significant contributions include
[Ahdra Merali](https://github.com/AhdraMeraliQB),
[Amanda Koh](https://github.com/amandakys),
[Andrew Mackay](https://github.com/Mackay031),
[Andrii Ivaniuk](https://github.com/andrii-ivaniuk),
[Anton Kirilenko](https://github.com/Flid),
[Antony Milne](https://github.com/antonymilne),
[Cvetanka Nechevska](https://github.com/cvetankanechevska),
[Dmitrii Deriabin](https://github.com/dmder),
[Gabriel Comym](https://github.com/comym),
[Gordon Wrigley](https://github.com/tolomea),
[Hamza Oza](https://github.com/hamzaoza),
[Ignacio Paricio](https://github.com/ignacioparicio),
[Jannic Holzer](https://github.com/jmholzer),
[Jo Stichbury](https://github.com/stichbury),
[Jiri Klein](https://github.com/jiriklein),
[Kiyohito Kunii](https://github.com/921kiyo),
[Laís Carvalho](https://github.com/laisbsc),
[Liam Brummitt](https://github.com/bru5),
[Lim Hoang](https://github.com/limdauto),
[Lorena Bălan](https://github.com/lorenabalan),
[Mehdi Naderi Varandi](https://github.com/MehdiNV),
[Nasef Khan](https://github.com/nakhan98),
[Nero Okwa](https://github.com/NeroOkwa),
[Richard Westenra](https://github.com/richardwestenra),
[Susanna Wong](https://github.com/studioswong),
[Vladimir Nikolic](https://github.com/vladimir-mck) and
[Zain Patel](https://github.com/mzjp2).


## Voting process

Voting can change TSC members and decide on the future of Kedro. The [voting members](#voting-members) of the TSC lead the process. The voting period is two week and through a GitHub discussion or through a pull request.

### Other issues or proposals

[Kedro's GitHub discussions](https://github.com/kedro-org/kedro/discussions) section is used to host votes on issues, proposals and changes affecting the future of Kedro. This includes amendments to our ways of working described on this page. These follow the [KEP voting process](https://github.com/kedro-org/kedro/discussions/5150).

### Adding or removing core datasets

The addition or removal of core datasets is done through a vote by the TSC. The voting process is described in the [kedro-datasets contribution guide](https://github.com/kedro-org/kedro-plugins/blob/main/kedro-datasets/CONTRIBUTING.md).

## Adding or removing TSC members

### Voluntary step-out
Any member may choose to step out of their current role at any time by communicating their decision to the TSC. No vote is required.

### Voluntary step-down
Any member may request to step down to a non voting category at any time if they believe they can contribute more effectively in that role. This change does not require a vote.

### Step-up procedure
Members who wish to move up to a category that requires a higher commitment (advisor to voting member or maintainer, or maintainer to voting member) must receive formal approval through a TSC vote. The member must also have an active TSC [voting member](#voting-members) advocate to support their nomination.

### Automatic removal and transition option
If a member is automatically removed from their current category (due to inactivity), they can request placement in the next lower level within two weeks of their removal. If no request is made within that time frame, the member will be removed from the TSC entirely.
