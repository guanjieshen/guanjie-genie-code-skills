## Organization Overview

Replace this with your org's universal Genie Code context — things that should apply in every workspace, regardless of team or environment.

Good candidates:
- House style for SQL (naming conventions, formatting preferences)
- Universally available data assets (e.g. `main.public.calendar` is your canonical date dimension)
- Standard caveats ("our financial year ends in March", "all timestamps stored UTC")
- Security/compliance constants ("never SELECT raw PII columns; use the `_masked` views")
- Where to find help ("file support tickets via #data-platform-help")

Keep entries terse — every character competes for the 20,000-char workspace instructions cap.
