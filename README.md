# Clockify to Payroll

This program processes a file, `clockify.xlsx`, located in the same directory, and formats it according to a configuration file, `config.yml`, for integration with payroll software.

## Configuration File Format

The `config.yml` file should follow this format ('#' indicates a comment):

```yml
users:
  # User with consistent pay across all tasks
  John Smith: # User's name as it appears in Clockify
    ID: 1 # Unique ID in the payroll system
    SSN: 123-45-6789 # Social Security Number (ID or SSN is mandatory, both are optional)
    Pay Designation: 1 # Payroll designation code
    Worked WG2 Code: 2 # Payroll WG2 code
  # User with variable pay based on task descriptions
  Jane Doe:
    ID: 3
    SSN: 987-65-4321
    Description:
      Website: # Specific task description
        Pay Designation: 2 # Payroll designation for this task
        Worked WG2 Code: 4 # Payroll WG2 code for this task
      Non Web: # Another task description
        Pay Designation: 4
        Worked WG2 Code: 6
```

If `config.yml` is missing on the first run, a template will be automatically created for you.

If a user has a `Description` in their configuration and additional task descriptions exist in `clockify.xlsx`, an error will occur to warn you.
