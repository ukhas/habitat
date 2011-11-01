# CHANGELOG #
## 0.1 a-year-in-the-making ##

- Initial release
- Parses documents, but with some mess. Hacked out of the ashes of a year`s work.

## 0.2 garden-pond ##

- Tests refactored and tidied up and improved
- Main refactored and renamed: the configuration file is now either specified
  by a single command line argument or found as `habitat.yml` in the current
  working directory. Its layout has changed slightly: see the example for
  details.
- Renamed modules: `filters/common` -> `filters`, `sensor_manager` ->
  `loadable_manager`
- Parser now only parses documents changed from startup onwards, rather than
  scouring the full history for unparsed documents.
- Breaking: sensor functions are now specified by a `sensor` key in flight
  documents, not `type`. Additionally, normal filter functions are now specified
  by `filter`, rather than `callable`
- Filters are now managed by `loadable_manager` (i.e., the old
  `sensor_manager`) and must be imported in the config file.
- Filters and sensors are separated in the manager by the `sensors` and
  'filters' namespaces. The parser and parser modules automatically prepend the
  relevant namespace when using a function, but this must be noted when
  configuring.
- Exception handling in the Parser was reorganised (internal).
