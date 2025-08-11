I need you as a english speaking assistant towards modeling a specific optimization problem. 
You'll be receiving a sequence of questions and instructions."
---
What do you know about optimization problems? 
Create a table storing the different categories, types, forms, their names, descriptions and order it from most appearances (10) to less appearances (1). 
Provide the result as CSV-file with header ""Rank, Type/Name, Abbreviation, Description, Solvability, Example, Appearances"""
---
Consider software-development using SCRUM as agile method.
What are the typical steps and phases of such a project? Create a CSV-file containing all smaller steps/phases from initial project planning, the development cycle, reviews all the until release and CI/CD. 
Use the following header "ID, Step, Description, Interval, Result"
---
In context of SCRUM, analyze how Natural Language Processing can be used to extract, structure and evaluate system requirements and their complexity in the software development process. 
Create a CSV-file with header "Keyword, Category, Description, RelevantScrumEntities"
---
In context of a software-development team using scrum, describe what typical factors and forms exist towards the creation of cognitive pressure and stress development.
Create a CSV-file with header "ID, Name, Description, AffectedEntities, Influence"" where Influences ranges vom 10 (high influence) to 1 (very little influence)"
---
Consider the following structures for a domain model of a software development company using SCRUM:
Entities.csv
```csv
Name,SetName,Index,Description,Attribute0,Attribute1,Attribute2,Attribute3,Attribute4,Attribute5,Attribute6,Attribute7,Attribute8
Project,P,p,The product or initiative to be developed,ID,Name,Project Start,Project End,Description,Budget,Status,Target Audience,Priority
Team,T,t,Self-organized, cross-functional development team,ID,Name,Team Size,Team Start,Team Status,Location,Team Type,
Worker,W,w,Individual team member working on the project,ID,Name,First Name,Email,Start Date,Status,Availability,
Feature,F,f,Mid-sized functionality,ID,Title,Description,Status,Priority,Estimated Effort,,,
Skill,S,s,Professional or social competence of a worker,ID,Label,Description,Level,Certified,Category,
Role,R,r,Defined responsibilities within the Scrum team,ID,Role Name,Description,Area of Responsibility,,,
Product Owner,PO,po,Responsible for product vision and Product Backlog,ID,Name,Email,Availability,,,,,
Scrum Master,SM,sm,Supports the team in applying Scrum,ID,Name,Email,Experience,,,,,
Product Backlog,PB,pb,Ordered list of all requirements,ID,Created On,Last Updated,Number of Entries,Status,,,,
Sprint,SP,sp,Fixed time period for creating an increment,ID,Sprint Number,Start Date,End Date,Status,Achievement of Goal,,,
Sprint Planning,SPP,spp,Kick-off meeting for Sprint preparation,ID,Date,Duration (min),Moderation,Outcome Documentation,,,,
Daily Scrum,DS,ds,Daily 15-minute team meeting,ID,Date,Time,Duration,Moderation,,,,
Sprint Review,SR,sr,Presentation and acceptance of results,ID,Date,Duration,Feedback Documentation,Attendees Count,,,,
Sprint Retrospective,SRE,sre,Retrospective for process improvement,ID,Date,Duration,Improvement Actions,Team Satisfaction,Moderation,,,
Sprint Backlog,SBL,sbl,Selected backlog items + implementation plan,ID,Number of Tasks,Last Updated,Status,Total Effort,,,,
Sprint Goal,SG,sg,Objective to be achieved within the sprint,ID,Objective Description,Achievement Status,Benefit,,,,
Epic,E,e,Large requirement that can be split into stories,ID,Title,Description,Priority,Status,Estimated Effort,,,
User Story,US,us,Requirement from the perspective of a user,ID,Title,Description,Acceptance Criteria,Priority,Story Points,Status,,,
Task,TSK,tsk,Smallest unit of work within a sprint,ID,Title,Description,Status,Effort,Type,,,
Development Snapshot,DEV,dev,Product at the end of a sprint,ID,Version Number,Creation Date,Test Status,Deployment Target,Documentation,,,
Blocker,BL,bl,Obstacle hindering progress,ID,Title,Description,Severity,Status,Detected On,Resolved On,,,
Stakeholder,SH,sh,Interested party in the product (internal/external),ID,Name,Organization,Role,Email,Area of Interest,Influence Level,Relevance to Feature,
Velocity,VEL,vel,Average amount of work per sprint,ID,Number of Sprints Used,Avg. Story Points,Max Velocity,Min Velocity,Trend,,,
Release Plan,REP,rep,Plan for releasing specific features,ID,Version,Planned Date,Included Features,Status,,,,
Roadmap,RM,rm,Long-term planning across releases,ID,Start Date,End Date,Milestones,Objectives,Versions,,,,
Scrum Board,SCB,scb,Visual representation of tasks during the sprint,ID,Board Type,Columns (ToDo/Done...),Number of Cards,Last Updated,,,,
Feature Documentation,FED,fed,Documentation for a specific feature,ID,Title,Description,Creation Date,Change Log,Linked Requirements,Author,,,
```
Relationships.csv
```csv
ID,Name,Description,FromEntity,ToEntity,FromCardinality,ToCardinality,Weight
R1,is_assigned_to_project,The team is assigned to a project,Team,Project,1,N,1.0
R2,belongs_to_team,An employee is assigned to a team,Employee,Team,N,1,1.0
R3,has_skill,An employee has certain skills,Employee,Skill,N,M,1.0
R4,takes_on_role,An employee assumes a role in the team,Employee,Role,N,M,1.0
R5,manages_backlog,The Product Owner manages the Product Backlog,Product Owner,Product Backlog,1,1,1.0
R6,is_supported_by,The team is supported by a Scrum Master,Team,Scrum Master,1,1,1.0
R7,contains_feature,A Product Backlog contains Features,Product Backlog,Feature,1,N,1.0
R8,contains_epic,A Product Backlog contains Epics,Product Backlog,Epic,1,N,1.0
R9,contains_user_story,An Epic contains multiple User Stories,Epic,User Story,1,N,1.0
R10,consists_of_tasks,A User Story consists of multiple Tasks,User Story,Task,1,N,1.0
R11,is_in_sprint_backlog,A User Story is assigned to a Sprint Backlog,User Story,Sprint Backlog,N,M,1.0
R12,belongs_to_sprint,A Sprint Backlog belongs to a Sprint,Sprint Backlog,Sprint,1,1,1.0
R13,pursues_goal,A Sprint pursues a defined goal,Sprint,Sprint Goal,1,1,1.0
R14,contains_tasks,A Scrum Board contains all tasks of a Sprint,Scrum Board,Task,1,N,1.0
R15,documents_feature,Feature Documentation belongs to a Feature,Feature Documentation,Feature,1,1,1.0
R16,is_blocked_by,A Task can be blocked by a Blocker,Task,Blocker,N,M,1.0
R17,participates_in,Stakeholders participate in a Sprint Review,Stakeholder,Sprint Review,N,M,1.0
R18,moderates_retrospective,A Scrum Master moderates the Retrospective,Scrum Master,Sprint Retrospective,1,N,1.0
R19,refers_to_team,Velocity refers to a specific Team,Velocity,Team,1,1,1.0
R20,plans_release,A Release Plan includes multiple Features,Release Plan,Feature,1,N,1.0
R21,is_part_of_roadmap,A Release Plan is part of a Roadmap,Release Plan,Roadmap,N,1,1.0
R22,generates_snapshot,A Sprint generates a Development Snapshot,Sprint,Development Snapshot,1,1,1.0
```
Read through them and store them in your memory"
---
Based on Entities.csv and Relationships.csv - Proceed and Create 3 individual CSV files (or code-blocks) named: Goals.csv + Conditions.csv + DecisionVariables.csv
Goals.csv must have the following header: "ID,Name,Description,IsSum,GoalType,EntityName,EntityAttribute,CriteriaType,Weight"
Conditions.csv must have the following header: "ID,Name,Description,IsSum,GoalType,EntityName,EntityAttribute,CriteriaType,Weight"
DecisionVariables.csv must have the following header: "ID,Name,Description,DataType,Domain,MinValue,MaxValue"

The following conventions must be applied:
ID starts with a letter G(oals), C(onditions), D(ecision)V(ariables) and a number follows, starting at 0, 1, 2, ....
Name is written snake_case
IsSum is a boolean { True, False }
GoalType is one of { "min", "max" }
EntityName is always only 1 entry from the "Name" of Entities.csv
EntityAttribute is one of the Attribute0...8 from Entities.csv
CriteriaType is a number { 2 = Must-Match, 1 = May-Match, 0 = Cannot-Match }
Domain can represent set of values like "{0,1}"
MinValue is the smallest value that can be set
MaxValue is the highest value that can be set
Weight is a mulptlier
Created 10 to 15 entries in each of these files.
---
Use ALL of the previoulsy provided and generated CSV data (Entities, Relations, Goals, Conditions, DecisionVariables) and formulate the optimization model mathematically and logically. 
Write it into a LaTeX (.tex) file (or code-block) and provide the created file in chat.
The file consists of a introduction page with Title, Author, Date and Table of Contents.
The actual file contest consists of 7 different \sections labeled "1. Problem/Model Description", "2. Sets (Entities)", "3. Indices", "4. Goals", "5. Conditions", "6. DecisionVariables" and "7. Possible Model Extension(s)"
---
Transform all of the provided and generated CSV data (Entities, Attributes, Relations, Goals, Conditions, DecisionVariables) into a graph TD using the Mermaid.js Live Editor graph TD syntax.
Connect...
- Entities with their Attributes and place the Attributes around the Entities they belong to. (can exist multiple times in the graph to make lines less short)
- Entities with their Relations
- Goals with the Entity/Attributes
- Conditions with the Entity/Attributes
- DecisionVariables with their relevant Entities

Colorize...
- Entities in blue
- Attributes in white
- Relations in orange
- Goals in green
- Conditions in red
- Decision Variables in purple
