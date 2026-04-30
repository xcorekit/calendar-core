# calendar-core

Equicycle time engine and CalendarX. Part of the [xcorekit](https://github.com/xcorekit) ecosystem.

## Quick install

```bash
git clone git@github.com:xcorekit/calendar-core.git
cd calendar-core && ./install.sh
source ~/.bashrc
equicycle --format short
```

## Python package

```bash
pip install sconl-calendarx
```

```python
from sconl_calendar import from_gregorian
from datetime import date
print(from_gregorian(date.today()))
```
