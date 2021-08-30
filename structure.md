# SAS Version 5 Transport Format

- All transport data set records are 80 bytes in length.
- If there is not sufficient  data to reach 80 bytes, then a record is padded with ASCII blanks to 80 bytes.
- All character data are stored in ASCII.
- All integers are stored using IBM-style integer format.
- All floating-point numbers are stored using the IBM-style double.
  - truncated if the variable's length is less than 8

## Structure

- First header record
- Real header records
- Member header records
- Member header data
- Namestr header record
- Namestr records
- Observation header
- Data records

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
HEADER RECORD*******LIBRARY HEADER RECORD!!!!!!!000000000000000000000000000000
SAS     SAS     SASLIB  6.06    bsd4.2                          13APR89:10:20:06
13APR89:10:20:06
HEADER RECORD*******MEMBER  HEADER RECORD!!!!!!!000000000000000001600000000140
HEADER RECORD*******DSCRPTR HEADER RECORD!!!!!!!000000000000000000000000000000
SAS     ABC     SASDATA 6.06    bsd4.2                          13APR89:10:20:06
13APR89:10:20:06
HEADER RECORD*******NAMESTR HEADER RECORD!!!!!!!000000000200000000000000000000
...
HEADER RECORD*******OBS     HEADER RECORD!!!!!!!000000000000000000000000000000
...
```

## Record Layout

### First header record

consists of the following character string, in ASCII.

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
HEADER RECORD*******LIBRARY HEADER RECORD!!!!!!!000000000000000000000000000000
```

### Real header records

#### First record

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
aaaaaaaabbbbbbbbccccccccddddddddeeeeeeee                        ffffffffffffffff
```

- `aaaaaaaa`: 'SAS'
- `bbbbbbbb`: 'SAS'
- `cccccccc`: 'SASLIB'
- `dddddddd`: SAS version
- `eeeeeeee`: Operating system
- `ffffffffffffffff`: date and time created, formatted as `ddMMMyy:hh:mm:ss`

as a C structure:

```c
struct REAL_HEADER {
    char sas_symbol[2][8];
    char saslib[8];
    char sasver[8];
    char sas_os[8];
    char blanks[24];
    char sas_create[16];
};
```

#### Second record

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
ddMMMyy:hh:mm:ss
```

- `ddMMMyy:hh:mm:ss`: datetime modified

### Member header records

Both of these records occur for every member in the transport file.

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
HEADER RECORD*******MEMBER  HEADER RECORD!!!!!!!000000000000000001600000000140
HEADER RECORD*******DSCRPTR HEADER RECORD!!!!!!!000000000000000000000000000000
```

- `0140`: This value specifies the size of the variable descriptor (NAMESTR) record.

### Member header data

#### First record

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
aaaaaaaabbbbbbbbccccccccddddddddeeeeeeee                        ffffffffffffffff
```

- `aaaaaaaa`: 'SAS'
- `bbbbbbbb`: data set name
- `cccccccc`: 'SASDATA'
- `dddddddd`: SAS version
- `eeeeeeee`: Operating system
- `ffffffffffffffff`: date and time created, formatted as `ddMMMyy:hh:mm:ss`

as a C structure:

```c
struct FIRST_MEMBER_HEADER {
    char sas_symbol[8];
    char sas_dsname[8];
    char sasdata[8];
    char sasver[8]
    char sas_osname[8];
    char blanks[24];
    char sas_create[16];
};
```

#### Second record

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
ddMMMyy:hh:mm:ss                aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabbbbbbbb
```

- `ddMMMyy:hh:mm:ss`: date and time modified
- `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`: blank-padded data set label
  - Only the first 40 characters are stored in the second header record.
- `bbbbbbbb`: blank-padded data set type

as a C structure:

```c
struct SECOND_MEMBER_HEADER {
    char dtmod_day[2];
    char dtmod_month[3];
    char dtmod_year[2];
    char dtmod_colon1[1];
    char dtmod_hour[2];
    char dtmod_colon2[1];
    char dtmod_minute[2];
    char dtmod_colon2[1];
    char dtmod_second[2];
    char padding[16];
    char dslabel[40];
    char dstype[8]
};
```

### Namestr header record

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
HEADER RECORD*******NAMESTR HEADER RECORD!!!!!!!000000xxxx00000000000000000000
```

- `xxxx`: Number of variables in the data set, displayed with blank-padded numeric characters.
  - e,g. 2 variables: `xxxx` = `0002`

### Namestr records

- Each namestr field is 140 bytes long.
- The fields are streamed together and broken in 80-byte pieces.
- If the last byte of the last namestr field does not fall in the last byte of the 80-byte record, the record is padded  with ASCII blanks to 80 bytes.
- length given in the last 4 bytes of the member header record indicates the actual number of bytes for the NAMESTR structure.

```text
       8      16      24      32      40      48      56      64      72      80      88      96     104     112     120     128     136
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+----
aabbccddeeeeeeeeffffffffffffffffffffffffffffffffffffffffgggggggghhiijj  kkkkkkkkllmmnnnnoooooooooooooooooooooooooooooooooooooooooooooooooooo
```

```c
struct NAMESTR {
    short ntype;        /* VARIABLE TYPE: 1=NUMERIC, 2=CHAR     */
    short nhfun;        /* HASH OF NNAME (always 0) */
    short nlng;         /* LENGTH OF VARIABLE IN OBSERVATION     */
    short nvar0;        /* VARNUM */
    char8 nname;        /* NAME OF VARIABLE */
    char40 nlabel;      /* LABEL OF VARIABLE */
    char8 nform;        /* NAME OF FORMAT  */
    short nfl;          /* FORMAT FIELD LENGTH OR 0 */
    short nfd;          /* FORMAT NUMBER OF DECIMALS */
    short nfj;          /* 0=LEFT JUSTIFICATION, 1=RIGHT JUST     */
    char nfill[2];      /* (UNUSED, FOR ALIGNMENT AND FUTURE)     */
    char8 niform;       /* NAME OF INPUT FORMAT  */
    short nifl;         /* INFORMAT LENGTH ATTRIBUTE */
    short nifd;         /* INFORMAT NUMBER OF DECIMALS */
    long npos;          /* POSITION OF VALUE IN OBSERVATION       */
    char rest[52];      /* remaining fields are irrelevant */
};
```

### Observation header

```text
       8      16      24      32      40      48      56      64      72      80
-------+-------+-------+-------+-------+-------+-------+-------+-------+-------+
HEADER RECORD*******OBS     HEADER RECORD!!!!!!!000000000000000000000000000000
```

### Data records

- streamed in the same way that namestrs are.
- ASCII blank padding at the end of the last record if necessary.
- No special trailing record.

## Missing Values

- Missing values are written out with the first byte (the exponent) indicating  the proper missing values.
- All subsequent bytes are `0x00`.

First byte:

|type|byte  |
|----|------|
|`._`|`0x5f`|
|`.` |`0x2e`|
|`.A`|`0x41`|
|`.B`|`0x42`|
|... |      |
|`.Z`|`0x5a`|

## Numeric data fields

- stored as floating-point numbers.
  - using the IBM mainframe representation.

## References

- [Record Layout of a SAS® Version 5 or 6 Data Set in SAS® Transport (Xport) Format](https://support.sas.com/content/dam/SAS/support/en/technical-papers/record-layout-of-a-sas-version-5-or-6-data-set-in-sas-transport-xport-format.pdf)
- [SAS®9.4ファイルの移動とアクセス(第2版)](https://www.sas.com/offices/asiapacific/japan/service/help/pdf/v94/movefile.pdf)
