# Dawnbrief daily routine

Once the skill is saved, create the routine by telling your Bot:

> Create a routine called "dawnbrief" that runs at 07:00 every weekday in my time zone. Each run: use the dawnbrief skill and send me the brief as one message. Don't take any action from the brief; wait for my replies.

Weekends: add a second routine at 09:00 on Saturday and Sunday with "calendar and NEEDS YOU only", or leave weekends off.

## Why once a day

Grok Bot routines can run as often as every 5 minutes, and each Bot can have up to 50. Routines share one weekly allowance with Cursor and the Grok apps, and people on Cursor's forum report running out within days and spilling into paid usage. A brief that reads a day's calendar, one night of email and up to 50 news items once a morning is a small job. Running it hourly would repeat that work 24 times a day.

We haven't been able to measure how much of the allowance one run uses, because we don't have a Grok Bot plan to test on. If you run it, please open an issue with what a week of runs used.

## Safety

- The routine only reads. Declines happen only when you reply "OK skip <meeting>".
- Keep one Bot on this job. Don't let two Bots trade messages about the brief.

Status: **not yet tested on Grok Bot.**
