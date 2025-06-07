# Jupyter Notebook Quizzes for Canvas

This project contains components that I use to make quizzes for my CIS-15 class
at Cabrillo College. It's built on top of
[nbtest](https://github.com/mike-matera/nbtest), a system for embedding
student-centered unit tests into notebooks. The primary functions of nbquiz are
to:

1. Define a format for test question banks built on top of nbquiz. 
1. Create assessments that can be imported into Canvas.
1. Provide a runtime that uses nbtest to check solutions while preventing
   students from seeing the tests being run.

This project is a part of my 2024-2025 sabbatical work. 

## Goals (and non-Goals)

My classes are online and in-person hybrid classes (also called HyFlex or
flexible hybrid) classes. In person attendance is encouraged but not required.
This poses difficult challenges in an introduction to programming class, where
cheating is easy and often rampant. In order to fairly assess how my students
are learning I give exams that are timed and randomized using Canvas' question
group function. Recently I've experimented with using prompt injection to foil
students who use generative A.I. 

The technical goals of the project follow from the overall goal of student
learning and success with added constraints based on how I teach the course. The
primary goals are:

1. Provide a safe way to run possibly malicious student code that works with the
   [Zero to JupyterHub with Kubernetes](https://z2jh.jupyter.org/en/stable/)
   runtime.
1. Export quizzes to Canvas LMS.

There are important non-goals:

1. No duplication of Canvas functionality, including assigning scores,
   submitting responses or keeping a grade book. 
1. The runtime is not suitable outside of z2jh (i.e. no authentication or secure
   communication is necessary)
1. Support for other LMSs

## Zero to JupyterHub with Kubernetes Integration

The service for checking solutions should run in its own container because it
contains secrets that should be kept away from students. The container must be a
sidecar because it runs with the same permissions as the user (making it safe
for the cluster).

### Per-user Sidecar

A per-user sidecar accompanies each notebook container enabling communication
over `localhost`. This keeps access local to the user, which is very safe.
Running sidecars is supported by z2jh. See the [configuration
reference](https://z2jh.jupyter.org/en/stable/resources/reference.html#singleuser)
specifies that additional container definitions can be passed to the single user
spawner:

[https://z2jh.jupyter.org/en/stable/resources/reference.html\#singleuser-extracontainers](https://z2jh.jupyter.org/en/stable/resources/reference.html#singleuser-extracontainers)

An example configuration is in the `test/z2jh-values.yaml` file. 


## Out of Band Grader Architecture

The simplified diagram shows the process model of the z2jh singleuser container
and associated grader sidecar. The sidecar has a server process that receives
code, manages the test execution and replies with results. The sidecar
implementation does not require authentication because it's local to the user's
pod and therefore tightly coupled to an existing system user. The grader gives
students advice and does not submit results for them, therefore there is no need
for the sidecar to authenticate to other services. The grader sidecar is
stateless for maximum flexibility and deployability. 

<img src="doc/checker-process-model.png" width=400 />

The process of handling student code and presenting results is shown in the
diagram below:

<img src="doc/checker-process.png" width=400 />

## Test Banks

Test question banks are valuable course material that are painstakingly updated
and maintained by faculty. Ideally students are exposed to novel questions in an
assessment, which is quite hard to do in an introduction to programming class.
This project is designed to help faculty make large test banks so that answers
aren't known. Nbquiz test banks should:

- Be compatible with Canvas.
- Be easy to read and write.
- Enable high question counts based on variations reuse.
- Support function-based and cell-based solutions.   
- Enable prompt injection.  

### Student's Perspective

A student is assigned a quiz in Canvas. The instructions for the quiz present a
downloadable blank notebook and, once started, a randomized set of questions.
Solutions are entered into the notebook where the checker is run. Once completed
the notebook is submitted into the quiz. 

### The Assessment Notebook 

Notebook cells identify the question and have a fillable docstring. Each
question is answered in its own cell and the checker cross references existing
cell tags against question specific ones. An answer cell that isn't tagged
properly generates a helpful error message. 

The assessment notebook looks a bit like this:

| This is the Midterm! | 
| :---- | 
| Here are some instructions written by the instructor. | 
| **Question 1** |
| `"""@question1 add tag here:"""` | 
| `%%testing @question1` | 
| **Question 2** |
| `"""@question2 add tag here:"""` | 
| `%%testing @question2` | 
| ... |

The number of questions in the blank assessment notebook will always match the
number of questions in the assessment. The assessment notebook marks all cells
non-deletable and all cells except for the solution cells as read-only. 

## Test Question Design 

Test questions are Python classes that bundle three key elements:

1. The question prompt. (i.e. *Write a function that...*)
1. Test cases that are run on the student's solution.
1. Parameters that enable variations of the question. (e.g. names and constants)

## Further Reading 

There is an example test bank that demonstrates the features of nbquiz in the 
`examples/testbanks/exam.ipynb` notebook. 
