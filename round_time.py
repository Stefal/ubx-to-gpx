import datetime

def round_time(dt=None, date_delta=datetime.timedelta(seconds=1), to='average'):
    """
    Round a datetime object to a multiple of a timedelta
    dt : datetime.datetime object, default now.
    dateDelta : timedelta object, we round to a multiple of this, default 1 minute.
    from:  http://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object-python
    """
    round_to = date_delta.total_seconds()
    if dt is None:
        dt = datetime.now()
    seconds = (dt - dt.min).seconds

    if seconds % round_to == 0 and dt.microsecond == 0:
        rounding = (seconds + round_to / 2) // round_to * round_to
    else:
        if to == 'up':
            # // is a floor division, not a comment on following line (like in javascript):
            rounding = (seconds + dt.microsecond/1000000 + round_to) // round_to * round_to
        elif to == 'down':
            rounding = seconds // round_to * round_to
        else:
            rounding = (seconds + round_to / 2) // round_to * round_to

    return dt + datetime.timedelta(0, rounding - seconds, - dt.microsecond)

# test data
print(round_time(datetime.datetime(2010,12,12,23,44,59,7769),to='average',date_delta=datetime.timedelta(milliseconds=1)))
print(round_time(datetime.datetime(2019,11,1,14,39,00), date_delta=datetime.timedelta(seconds=30), to='up'))
print(round_time(datetime.datetime(2019,11,2,14,39,00,1), date_delta=datetime.timedelta(seconds=30), to='up'))
print(round_time(datetime.datetime(2019,11,3,14,39,00,776980), date_delta=datetime.timedelta(seconds=30), to='up'))
print(round_time(datetime.datetime(2019,11,4,14,39,29,776980), date_delta=datetime.timedelta(seconds=30), to='up'))
print(round_time(datetime.datetime(2018,11,5,14,39,00,776980), date_delta=datetime.timedelta(seconds=30), to='down'))
print(round_time(datetime.datetime(2018,11,6,14,38,59,776980), date_delta=datetime.timedelta(seconds=30), to='down'))
print(round_time(datetime.datetime(2017,11,7,14,39,15), date_delta=datetime.timedelta(seconds=30), to='average'))
print(round_time(datetime.datetime(2017,11,8,14,39,14,999999), date_delta=datetime.timedelta(seconds=30), to='average'))
print(round_time(datetime.datetime(2019,11,9,14,39,14,999999), date_delta=datetime.timedelta(seconds=30), to='up'))
print(round_time(datetime.datetime(2012,12,10,23,44,59,7769),to='average'))
print(round_time(datetime.datetime(2012,12,11,23,44,59,7769),to='up'))
print(round_time(datetime.datetime(2010,12,12,23,44,59,7769),to='down',date_delta=datetime.timedelta(seconds=1)))
print(round_time(datetime.datetime(2011,12,13,23,44,59,7769),to='up',date_delta=datetime.timedelta(seconds=1)))
print(round_time(datetime.datetime(2012,12,14,23,44,59),date_delta=datetime.timedelta(hours=1),to='down'))
print(round_time(datetime.datetime(2012,12,15,23,44,59),date_delta=datetime.timedelta(hours=1),to='up'))
print(round_time(datetime.datetime(2012,12,16,23,44,59),date_delta=datetime.timedelta(hours=1)))
print(round_time(datetime.datetime(2012,12,17,23,00,00),date_delta=datetime.timedelta(hours=1),to='down'))
print(round_time(datetime.datetime(2012,12,18,23,00,00),date_delta=datetime.timedelta(hours=1),to='up'))
print(round_time(datetime.datetime(2012,12,19,23,00,00),date_delta=datetime.timedelta(hours=1)))

