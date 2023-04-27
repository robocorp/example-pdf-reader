*** Settings ***
Library     PDF_extras.py


*** Tasks ***
Read PDF Fields
    ${fields}=    Get Fields    resources/example.pdf
    FOR    ${key}    ${value}    IN    &{fields}
        No Operation
    END
