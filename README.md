# Uploading to report.ci

The REST Api of report.ci is as simple as can be, it consists of one endpoint:

`api.report.ci/publish`

## `GET` 

Yields the plan & installation ID if a token is provided

## `POST`

Upload the actual data. There is no `PATCH` because the Github Check API overwrites check runs if they have the same name. 
Thus reuploading a second check run to github will update the new run, while keeping the date for the old one alive.

### Authentication

The token shall be passed as `Bearer` in the `Authorization` http header. 
*Note that public projects work without a token on some CI systems.*

### Parameters

| Name | Description |
|------|-------------|
| `build-id` | The Build id used by the CI system when commiting data without a token |
| `owner` | The github handle of the repository owner | 
| `repo` | The repository name |
| `head-sha' | The hash of the commit this build is done for |
| `framework` | The framework identifier ['boost'] |
| `root-dir` | The root directory of the git-project, needed the test framework uses absolute paths |
| `service` | If a known CI system is used, it's identifier (i.e. `appveyor`, `travis` or `circle-ci`) | 