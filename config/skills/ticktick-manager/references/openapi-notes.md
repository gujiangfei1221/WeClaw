# Dida365 / TickTick OpenAPI Notes

This reference is for quick implementation and troubleshooting.

## Base URL

- Recommended: `https://api.dida365.com/open/v1`

## Auth

Use OAuth 2.0 Bearer token:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Frequently Used Endpoints

> Endpoint naming may evolve; verify against official docs if errors occur.

- List projects: `GET /project`
- Get project details and task data: `GET /project/{projectId}/data`
- Create task: `POST /task`
- Update task: `POST /task/{taskId}`
- Complete task: `POST /project/{projectId}/task/{taskId}/complete`
- Delete task: `DELETE /project/{projectId}/task/{taskId}`

## OAuth Refresh

- Token endpoint: `POST https://dida365.com/oauth/token`
- Content-Type: `application/x-www-form-urlencoded`
- Parameters: `client_id`, `client_secret`, `grant_type=refresh_token`, `refresh_token`, `redirect_uri`

## Task Fields (common)

- `projectId` (string)
- `title` (string, required)
- `content` (string, optional)
- `desc` (string, optional)
- `isAllDay` (boolean, optional)
- `startDate` (datetime string, optional)
- `dueDate` (datetime string, optional)
- `timeZone` (string, optional)
- `reminders` (list, optional)
- `repeatFlag` (string, optional)
- `priority` (number, optional)
- `sortOrder` (number, optional)
- `items` (list, optional)

时间格式使用官方格式：`yyyy-MM-dd'T'HH:mm:ssZ`

示例：`2026-03-10T21:00:00+0800`

## Practical Tips

- Always start with listing projects to find the correct `projectId`.
- For timed tasks, prefer `isAllDay=false` with `startDate`, `dueDate`, and `timeZone`.
- If you want a visible reminder time in TickTick, do not rely on `title` alone; send the proper time fields too.
- Use official datetime format with timezone offset, e.g. `2026-03-10T21:00:00+0800`.
- For immediate reminder at the specified time, `reminders` can include `"TRIGGER:PT0S"`.
- Log status code and response body for debugging.
