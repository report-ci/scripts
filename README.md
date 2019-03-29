# Getting started

**See https://report.ci for more information and to sign up and use https://github.com/apps/report-ci to install the github app.**

# Endpoints

## Publishing endpoint report.ci

The REST Api of report.ci is as simple as can be, it consists of one endpoint:

`https://report.ci/publish`

### `GET` 

Yields the plan & installation ID if a token is provided

### `POST`

Upload the actual data.  Thus reuploading a second check run to github will update the new run, while keeping the date for the old one alive.

### `PATCH`

Upload the a test report and overwrite an existing change. Required when used with scheduling.

#### Authentication

The token shall be passed as `Bearer` in the `Authorization` http header. 
*Note that public projects work without a token on some CI systems.*

#### Parameters

| Name | Description |
|------|-------------|
| `build-id` | The Build id used by the CI system when commiting data without a token |
| `owner` | The github handle of the repository owner | 
| `repo` | The repository name |
| `head-sha` | The hash of the commit this build is done for |
| `framework` | The framework identifier ['boost'] |
| `root-dir` | The root directory of the git-project, needed the test framework uses absolute paths |
| `service` | If a known CI system is used, it's identifier (i.e. `appveyor`, `travis` or `circle-ci`) |
| `branch` | If a branch is known, this allows the usage of badges | 
| `check-run-id` | The id given by github, which is required to overwrite a check_run using the `PATH` endpoint. |
