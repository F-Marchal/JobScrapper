# Tools
This folder contains standalone tools, classes and functions that can be used
by any part of this app.

---
# geolocalisation.py
This file contains a `Geolocalisation` class that act as a wrapper for both 
geopy / Nominatim services and for the `Distances` / `Places` table.

The main functionalities of this class is the `geolocate` method that returns coordinates
of place using either a database or geopy services.