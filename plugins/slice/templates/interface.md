# Interface

Status: draft

Stack: <language and style of the surface, for example HTTP JSON API, or a Python module>

## Surface

The test writer sees only this file, not the code. Give it all that it must know to call the surface.

- `<import line, or METHOD /path>`: `<signature, or the request and response shapes>`. Types: <types>. Errors: <error form>. Exposes: <domain concepts from domain.md>.

The stubs fail with the not-implemented error of the stack. The message holds "not implemented".

`Status: draft` becomes `Status: approved` only after the user approves the surface, before the test writer runs.

## Security

<the OWASP Top 10 protection that this surface needs, in the idiom of the stack: for example input validation, access control, no secret in output, safe queries>

## S1

- Uses: <the parts of the surface that S1 calls>
- Stubs: <the files that hold the stubs>
- Changed: <none, or the requirement IDs (R1, R2) of the entries that already exist and change: their tests can fail by assertion>
