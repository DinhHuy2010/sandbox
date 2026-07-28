import faker
import icalendar

fak = faker.Faker()
calc = icalendar.Calendar()
calc.add("prodid", f"//icalendar-{icalendar.__version__}//example.org")
# print(calc.to_ical().decode("utf-8"))

for i in range(10):
    event = icalendar.Event()
    event.add("summary", fak.sentence())
    event.add("dtstart", fak.date_time_this_year())
    event.add("dtend", fak.date_time_this_year())
    event.add("description", fak.text())
    calc.add_component(event)
with open("example.ics", "wb") as f:
    f.write(calc.to_ical())
