DataPrime
Concept
DataPrime is a language that allows to query data by describing a series of operations on it.

This concept is very similar to how the bash command line operates in Linux, allowing the user to compose a set of small processes into a solution that describes what the user needs.

Query Format
Query format is as follows:

source logs | operator ... | operator ... | operator | ...
Any whitespace between operators is ignored, allowing you to write queries as multiline queries that are more readable. For example:

source logs
  | operator1 ....
  | operator2 ....
  | ...
Data Types
These are the data types currently supported:

string
number/num - A number (double or integer)
boolean - A boolean type, with true or false values
null - A null value
timestamp - A UTC timestamp in nanoseconds
interval - A time span in nanoseconds
Sources
source
Set the data source that your DataPrime query is based on.

source <dataset> [<timeframe>]
Example of datasets: logs, spans

An optional timeframe can be specified to limit the data to a specific time range.

Examples:

source logs
Timeframe
Parameters $p.timeRange.startTime, and $p.timeRange.endTime are available throughout the query, referencing the corresponding time-picker values.

around
Select events around a specific timestamp and, optionally, within a specified interval. Timestamps can be any valid expressions resulting in a constant of timestamp type. Default interval is 30 minutes.

source logs around <time-expr> [interval <interval>]
Examples:

source logs around @'2021-01-01T00:00:00Z' interval 1h
source logs around (@'now'/1d) - 30d
between
Select events between two timestamps. Timestamps can be any valid expressions resulting in a constant of timestamp type.

source logs between <start-time-expr> and <end-time-expr>
Examples:

source logs between @'2021-01-01T00:00:00Z' and @'2021-01-02T00:00:00Z'
source logs between @'now'-7d and @'now'
last
Select events from the last <interval>.

source logs last <interval>
Examples:

source logs last 1d
source logs last 10h5m30s
timeshifted
Select events that are shifted in time WRT context time range by the specified interval.

source logs timeshifted <interval>
Examples:

source logs timeshifted 1h # shifts forward by 1 hour
source logs timeshifted -1d # shifts back by 1 day
Operators
aggregate
Calculates aggregations over input.

aggregate <aggregation_expression> [as <result_keypath>] [, <aggregation_expression_2> [as <result_keypath_2], ...]
For example, the following query:

aggregate count() as count, max($d.duration) as max_duration
Will result in logs in the following format:

{ "count": 42, "max_duration": 54071 }
Supported aggregation functions are listed in Aggregation Functions section.

block
The negation of filter. Filters-out all events where the condition is true. The same effect can be achieved by using filter with !(condition).

block $d.status_code >= 200 && $d.status_code <= 299         # Leave all events which don't have a status code of 2xx
bottom
No grouping variation
Limits the rows returned to a specified number and order the result by a set of expressions.

order_direction := "descending"/"ascending" according to top/bottom

bottom <limit> <result_expression1> [as <alias>] [, <result_expression2> [as <alias2>], ...] by <orderby_expression> [as alias>]
For example, the following query:

bottom 5 $m.severity as $d.log_severity by $d.duration
Will result in logs of the following form:

[
   { "log_severity": "Debug", "duration":  1000 }
   { "log_severity": "Warning", "duration": 2000 },
   ...
]
Grouping variation
Limits the rows returned to a specified number and group them by a set of aggregation expressions and order them by a set of expressions.

order_direction := "descending"/"ascending" according to top/bottom

bottom <limit> <groupby_expression1> [as <alias>] [, <groupby_expression2> [as <alias2>], ...] [, <aggregatation_expression3> [as <alias3>], ...] by <aggregation_expression4> [as <alias>]
For example, the following query:

bottom 10 $m.severity, count() as $d.number_of_severities by avg($d.duration) as $d.avg_duration
Will result in logs of the following form:

[
   { "severity": "Warning", "number_of_severities": 50, avg_duration: 1000 },
   { "severity": "Debug", "number_of_severities":  10, avg_duration: 2000 }
   ...
]
Supported aggregation functions are listed in "Aggregation Functions" section.

choose
Leave only the keypaths provided, discarding all other keys. Fully supports nested keypaths in the output.

choose <keypath1> [as <new_keypath>],<keypath2> [as <new_keypath>],...
Examples:

choose $d.mysuperkey.myfield
choose $d.my_superkey.mykey as $d.important_value, 10 as $d.the_value_ten
convert
Convert the data types of keys.

The datatypes keyword is optional and can be used for readability.

(conv|convert) [datatypes] <keypath1>:<datatype1>,<keypath2>:<datatype2>,...
Examples:

convert $d.level:number
conv datatypes $d.long:number,$d.lat:number
convert $d.data.color:number,$d.item:string
count
Returns a single row containing the number of rows produced by the preceding operators.

count [into <keypath>]
An alias can be provided to override the keypath the result will be written to.

For example, the following part of a query

count into $d.num_rows
will result in a single row of the following form:

{ "num_rows": 7532 }
countby
Returns a row counting all the rows grouped by the expression.

countby <expression> [as <alias>] [into <keypath>]
An alias can be provided to override the keypath the result will be written into.

For example, the following part of a query

countby $d.verb into $d.verb_count
will result in a row for each group.

It is functionally identical to

groupby $d.verb aggregate count() as $d.verb_count
create
Create a new key and set its value to the result of the expression. Key creation is granular, meaning that parent keys in the path are not overwritten.

  (a|add|c|create) <keypath> from <expression>
Alternative syntax:

 (a|add|c|create) <expression> as <keypath>
Examples:

create $d.radius from 100+23
c $d.log_data.truncated_message from $d.message.substr(1,50)
c $d.trimmed_name from $d.username.trim()

create $d.temperature from 100*23

create 100*23 as $d.temperatur
create $m.severity as meta_severity
dedupeby
Deduplicate events based on a combination of expressions.

dedupeby <expr_1> [, <expr_2> ...] [keep N] [orderby <orderby_expr_1> [(asc|desc)] [, <orderby_expr_2> [(asc|desc)]]]
Returns N events for each distinct combination of the provided expressions.

<expr_N>: The expressions to deduplicate by.
N: The number of events to keep for each distinct combination. Default is 1.
<orderby_expr_N>: The expressions to order by.
(asc|desc): The order direction. Default is asc.
The content of the events are unchanged.

Example:

dedupeby $d.key
dedupeby $d.key keep 2
dedupeby $d.key1, $d.key2 keep 2 orderby $d.key asc, $d.key1 + $d.key2
distinct
Returns one row for each distinct combination of the provided expressions.

distinct <expression> [as <alias>] [, <expression_2> [as <alias_2>], ...]
This operator is functionally identical to groupby without any aggregate functions.

enrich
Enrich your logs using additional context from a lookup table.

Upload your lookup table using the Data Flow > Data Enrichment > Custom Enrichment section. For more details, see Custom Enrichment documentation.

enrich <value_to_lookup> into <enriched_key> using <lookup_table>
value_to_lookup - A string expression that will be looked up in the lookup table.
enriched_key - Destination key to store the enrichment result in.
lookup_table - The name of the Custom Enrichment table to be used.
The table's columns will be added as sub-keys to the destination key. If value_to_lookup is not found, the destination key will be null. You can then filter the results using the DataPrime capabilities, such as filtering logs by specific value in the enriched field.

Example:

The original log:

{
    "userid": "111",
    ...
}
The Custom Enrichment lookup table called my_users:

ID	Name	Department
111	John	Finance
222	Emily	IT
Running the following query:

enrich $d.userid into $d.user_enriched using my_users
Gives the following enriched log:

{
    "userid": "111",
    "user_enriched": {
        "ID": "111",
        "Name": "John",
        "Department": "Finance"
    },
    ...
}
Notes:

Run the DataPrime query source <lookup_table> to view the enrichment table.
If the original log already contains the enriched key:
If <value_to_lookup> exists in the <lookup_table>, the sub-keys will be updated with the new value. If the <value_to_lookup> does not exist, their current value will remain.
Any other sub-keys which are not columns in the <lookup_table> will remain with their existing values.
All values in the <lookup_table> are considered to be strings. This means that:
The <value_to_lookup> must be in a string format.
All values are enriched in a string format. You may then convert them to your preferred format (e.g. JSON, timestamp) using the appropriate functions.
For more information, see the enrich section in the DataPrime Glossary.

explode
Explodes an array of N elements into N documents, each containing one element of the array in the specified keypath.

explode <expression> into <keypath> [original discard|preserve]
expression - The array to explode.
keypath - Destination keypath to hold an element of exploded array.
Original document's fields can be either discarded, or preserved with original discard, or original preserve respectively. If omitted, the default behavior is original discard.

When preserving original fields, if destination keypath already exists, it will be overwritten with an exploded value.

Example:

Given logs:

{ "userid": "1", "scopes": ["read", "write"] }
{ "userid": "2", "scopes": ["read", null] }
Following query:

source logs | explode $d.scopes into $d.scope original preserve
Results in:

{ "userid": "1", "scope": "read" }
{ "userid": "1", "scope": "write" }
{ "userid": "2", "scope": "read" }
{ "userid": "2", "scope": null }
Whereas following query:

source logs | explode $d.scopes into $d.scope original discard
Results in:

{ "scope": "read" }
{ "scope": "write" }
{ "scope": "read" }
{ "scope": null }
extract
Extract data from some string value into a new object.

(e|extract) <expression> into <keypath> using <extraction-type>(<extraction-params>) [datatypes keypath:datatype,keypath:datatype,...]
It is possible to provide datatype information as part of the extraction, by using the datatypes clause.

Supported extraction methods are listed in Extractor Functions.

Examples:

extract $d.my_text into $d.my_data using regexp(e=/user (?<user>.*) has logged in/)

extract $d.my_string into $d.all_numbers using multi_regexp(/\d+/)

extract $d.text into $d.my_kvs using kv()
extract $d.text into $d.my_kvs using kv(pair_delimiter=' ',key_delimiter='=')
extract $d.my_msg into $d.data using kv() datatypes my_field:number

extract $d.json_message_as_str into $d.json_message using jsonobject(max_unescape_count=1)

extract $d.message into $d.codes using split(',', number)
Extracted data always goes into a new keypath as an object, allowing further processing of the new keys inside that new object. For example:

# Assuming a dataset which look like that:
{ "msg": "query_type=fetch query_id=100 query_results_duration_ms=232" }
{ "msg": "query_type=fetch query_id=200 query_results_duration_ms=1001" }

# And the following DataPrime query:
source logs
  | extract $d.msg into $d.query_data using kv() datatypes query_results_duration_ms:number
  | filter $d.query_data.query_results_duration_ms > 500

# The results will contain only the second message, in which the duration is larger than 500 ms
filter
Filter events, leaving only events for which the condition evaluates to true.

(f|filter|where) <condition-expression>
Examples:

f $d.radius > 10
filter $m.severity.toUpperCase() == 'INFO'
filter $l.applicationname == 'recommender'
filter $l.applicationname == 'myapp' && $d.msg.contains('failure')
groupby
Groups the results of the preceding operators by the specified grouping expressions and calculates aggregate functions for every group created.

groupby <grouping_expression> [as <alias>] [, <grouping_expression_2> [as <alias_2>], ...] [aggregate]
  <aggregation_expression> [as <result_keypath>]
  [, <aggregation_expression_2> [as <result_keypath_2], ...]
For example, the following query:

groupby $m.severity aggregate sum($d.duration)
Will result in logs of the following form:

{ "severity": "Warning", "_sum": 17045 }
The keypaths for the grouping expressions will always be under $d. Using the as keyword, we can rename the keypath for the grouping expressions and aggregation functions. The following query:

groupby $l.applicationname as $d.app aggregate sum($d.duration) as $d.sum_duration
Will result in logs of the following form:

{ "app": "web-api", "sum_duration": 17045 }
Supported aggregation functions are listed in Aggregation Functions section.

join
Join two queries based on a condition.

join [modifier] (<right_side_query>) on <condition> into <right_side_target>
join [modifier] (<right_side_query>) using <join_keypath_1> [, <join_keypath_2>, ...] into <right_side_target>
join cross (<right_side_query>) into <right_side_target>
modifier - The type of join to perform. Possible values are left, inner, full and cross. Defaults to left.
right_side_query - The right side query to join with. The current query is the left side.
condition - The condition to join on.
join_keypath_N - Join on these keypaths. Equvalent to condition on left=><join_keypath_1> == right=><join_keypath_1> && left=><join_keypath_2> == right=><join_keypath_2>
right_side_target - The keypath to store the right side of the join result.
The join operator allows you to combine the events of the current (left) query with those of another (right) query based on a condition. For each event of the left query, the join operator will select an event of the right query to satisfy the condition. The matching event from the right side will be stored in the specified keypath in the event of the left query, overriding any existing data stored there. If no event is found in the other query that satisfies the condition, the keypath will be null.

The condition
In the condition, you can use the left=> and right=> prefixes to refer to the events of the left and right queries, respectively. However, it is not required if a keypath exists in only one of the queries.

Each == comparison must be between a keypath of the left query and a keypath of the right query, but as the keypaths have to either be unique or prefixed with left=> or right=>, the orientation of the keypaths around == is not important.

Example:

Events of source users:

{ "id": "111", "name": "John" }
{ "id": "222", "name": "Emily" }
{ "id": "333", "name": "Alice" }
Events of source logins:

{ "userid": "111", "timestamp": "2022-01-01T12:00:00Z" }
{ "userid": "111", "timestamp": "2022-01-01T12:30:00Z" }
{ "userid": "222", "timestamp": "2022-01-01T13:00:00Z" }
{ "userid": "222", "timestamp": "2022-01-01T13:00:00Z" }
{ "userid": "222", "timestamp": "2022-01-01T13:00:00Z" }
source users | join (source logins | countby userid) on id == userid into logins
Results:

{ "id": "111", "name": "John", "logins": { "userid": "111", "_count": 2 } }
{ "id": "222", "name": "Emily", "logins": { "userid": "222", "_count": 3 } }
{ "id": "333", "name": "Alice", "logins": null }
Limitations
Join condition only supports keypath equality. Multiple equality conditions can be combined with &&.
One of the join side should be small (maximum a few hundred MB). Reduce the size by filtering or deleting unwanted fields.
Left outer joins require all columns in the condition (e.g., a == b && ... && x == y) to have non-null values. If any column in the join condition is nullable, rows with null values will not be joined, even when both sides contain null.
limit
Limits the output to the first <event-count> events.

limit <event-count>
Examples

limit 100
move
Move a key (including its child keys, if any) to a new location.

(m|move) <source-keypath> to <target-keypath>
Examples:

move $d.my_data.hostname to $d.my_new_data.host
m $d.kubernetes.labels to $d.my_labels
multigroupby
Groups the results of the preceding operators by the specified grouping set(s) and calculates aggregate functions for every group created.

multigroupby
  (<grouping_expression_1> as <alias> [, <grouping_expression_2> as <alias_2>, ...])
  [, (<grouping_expression_1> as <alias> [, <grouping_expression_2> as <alias_2>, ...]), ...]
[aggregate]
  <aggregation_expression> [as <result_keypath>] [, <aggregation_expression_2> [as <result_keypath_2], ...]
Note: Alias is optional when grouping expression is a Keypath.

Supported aggregation functions are listed in Aggregation Functions section.

orderby/sortby/order by/sort by
Sort the data by ascending/descending order of the expression value. Ordering by multiple expressions is supported.

(orderby|sortby|order by|sort by) <expression> [(asc|desc)] , ...
Examples:

orderby $d.myfield.myfield
orderby $d.myfield.myfield:number desc
sortby $d.myfield desc
NOTE: Sorting numeric values can be done by casting expression to the type: e.g.<expression>: number. In some cases, this will be inferred automatically by the engine.

redact
Replace all substrings matching a regexp pattern from some keypath value, effectively hiding the original content.

The matching keyword is optional and can be used to increase readability.

redact <keypath> [matching] /<regular-expression>/ to '<redacted_str>'
redact <keypath> [matching] <string> to '<redacted_str>'
Examples:

redact $d.mykey /[0-9]+/ to 'SOME_INTEGER'
redact $d.mysuperkey.user_id 'root' to 'UNKNOWN_USER'
redact $d.mysuperkey.user_id matching 'root' to 'UNKNOWN_USER'
remove
Remove a keypath from the object.

r|remove <keypath1> [ "," <keypath2> ]...
Examples:

r $d.mydata.unneeded_key
remove $d.mysuperkey.service_name, $d.mysuperkey.unneeded_key
replace
Replace the value of some key with a new value.

replace <keypath> with <expression>
Examples:

replace $d.message with null
replace $d.some_superkey.log_length_plus_10 with $d.original_log.length()+10
stitch
Zip 2 datasets row by row. Stitching will be done on an ordered row-by-row basis, with nulls on each side when the number of rows is different.

target - keypath where the right side of the stitch will be stored
merge - optional boolean merge flag, indicating a deep nested merge from the right hand side into lhs (at the target position)
Example:

Dataset A:

[{"a": 1}, {"a": 2}]
Dataset B:

[{"b": 1}, {"b": 2}]
source A | stitch (source B) into target

[
  {"a": 1, "target":{"b": 1}},
  {"a": 2, "target":{"b": 2}}
]
source A | stitch (source B) into $d merge

[
  {"a": 1, "b": 1},
  {"a": 2, "b": 2}
]
top
No grouping variation
Limits the rows returned to a specified number and order the result by a set of expressions.

order_direction := "descending"/"ascending" according to top/bottom

top <limit> <result_expression1> [as <alias>] [, <result_expression2> [as <alias2>], ...] by <orderby_expression> [as alias>]
For example, the following query:

top 5 $m.severity as $d.log_severity by $d.duration
Will result in logs of the following form:

[
   { "log_severity": "Warning", "duration": 2000 },
   { "log_severity": "Debug", "duration":  1000 }
   ...
]
Grouping variation
Limits the rows returned to a specified number and group them by a set of aggregation expressions and order them by a set of expressions.

order_direction := "descending"/"ascending" according to top/bottom

top <limit> <groupby_expression1> [as <alias>] [, <groupby_expression2> [as <alias2>], ...] [, <aggregatation_expression3> [as <alias3>], ...] by <aggregation_expression4> [as <alias>]
For example, the following query:

top 10 $m.severity, count() as $d.number_of_severities by avg($d.duration) as $d.avg_duration
Will result in logs of the following form:

[
   { "severity": "Debug", "number_of_severities":  10, avg_duration: 2000 }
   { "severity": "Warning", "number_of_severities": 50, avg_duration: 1000 },
   ...
]
Supported aggregation functions are listed in "Aggregation Functions" section.

union
Union a query.

union (<query>)
The union operator allows you to combine the results of the current query with those of a subquery.

Example:

Events of source users:

{ "userId": 1 }
{ "userId": 2 }
{ "userId": 3 }
Events of source premium_users:

{ "userId": 10 }
{ "userId": 20 }
{ "userId": 30 }
source users | join (source premium_users)
Results:

{ "userId": 1 }
{ "userId": 2 }
{ "userId": 3 }
{ "userId": 10 }
{ "userId": 20 }
{ "userId": 30 }
Note: the order of results is not deterministic.

Text Search Operators
find/text
Search for the string in a certain keypath.

(find|text) <free-text-string> in <keypath>
Examples:

find 'host1000' in $d.kubernetes.hostname
text 'us-east-1' in $d.msg
lucene
A generic lucene-compatible operator, allowing both free and wild text searches, and more complex search queries.

lucene <lucene-query-as-a-string>
Examples:

lucene 'pod:recommender AND (is_error:true OR status_code:404)'
lucene 'coralogix.metadata.severity:[Info TO *]'
lucene 'pod_name:(+app -cron)'
To search on a specific field, use the : or = operator. Most field names inside the lucene query are relative to $d (the root level of user-data). Certain special field names such as coralogix.metadata.severity correspond to fields under $m or $l. Whether a specific term matches a particular document is dependent on how a field is configured.

lucene 'rpc.type:grpc'
lucene 'pod_name=bar'
lucene 'ip:192.168.1.0/22'
lucene 'coralogix.metadata.severity:Info'
To search for multiple terms with a field we can use brackets to group multiple terms. Search terms can be negated with the - operator.

lucene 'status_code:(404 403)'
lucene 'status_code:-200'
Bounds can be expressed using the < or > operators or range queries. Range queries surrounded by square brackets, [ and ], are inclusive of the limit, whereas a curly brace, { and }, exclude the limit values. Braces can also be mixed to express whether either side of the limit should be inclusive. The wildcard character, *, signifies an open limit.

lucene 'status_code:>200'
lucene 'status_code:(>200 <400)'
lucene 'coralogix.metadata.severity:[Warning TO *]'
lucene 'ip:{192.168.0.1 TO *]'
To search using a regular expression, the / delimeter can be used.

lucene 'logger_name:/mycomp*ny/'
The special keyword _exists_ can be used to search for the a non-null value on a field.

lucene '_exists_:pod_name'
Multiple clauses can be combined using the AND or OR operators.

lucene '_exists_:pod_name AND status_code:(-200)'
lucene 'status_code:[0 TO *] OR is_error:true'
wildfind/wildtext
Search for the string in the entire user data. This can be used when the keypath in which the text resides is unknown.

NOTE: The performance of this operator is worse than when using the find/text operator. Prefer using those operators when you know the keypath to search for.

(wildfind/wildtext) <string>
Examples:

wildfind 'my-region'
wildfind ':9092'
Expressions
DataPrime supports a limited set of javascript constructs that can be used in expressions.

The data is exposed using the following top-level fields:

$m - Event metadata
timestamp
severity - Possible values are Verbose, Debug, Info, Warning, Error, Critical
priorityclass - Possible values are high, medium, low
logid
$l - Event labels
applicationname
subsystemname
category
classname
computername
methodname
threadid
ipaddress
$d - The user's data
Language Constructs
All language constructs that are supported:

Constants: strings, numbers, booleans, regular expressions, null
Nested field access
Basic math operations: +, -, *, \, %
Boolean operations: &&, ||, !
Equality and comparison: ==, !=, <, <=, >, >=
Text search: ~, ~~
String interpolation
Timestamp expressions and interval literals
Casting an expression to a desired data type: e.g. $d.temperature:number. Type inference is automatically applied when possible to reduce the need for casting.
Field Access
Accessing nested data is done by using a keypath, similar to any programming language or json tool. Keys with special characters can be accessed using a map-like syntax, with the key string as the map index, e.g. $d.my_superkey['my_field_with_a_special/character'].

Examples:

$m.timestamp
$d.my_superkey.myfield
$d.my_superkey['my_field_with_a_special/character']
$l.applicationname
String Interpolation
`this is an interpolated {$d.some_keypath} string` - {$d.some_keypath} will be replaced with the evaluated expression that is wrapped by the brackets
`this is how you escape \{ and \} and \`` - Backward slash (\) is used to escape characters like {, } that are used for keypaths.
Text Search
Boolean expressions for text search:

$d.field ~ 'text phrase' - case-insensitive search for a text phrase in a specific field.
$d ~~ 'text phrase' - case-insensitive search for a text phrase in $d.
Timestamp Expressions
Expressions prefixed by @ are timestamp expressions and always return a timestamp. They can be either literals (@number or @'string') which are validated at query compilation time, or dynamic expressions (@expression) which is evaluated at query runtime based on the expression's data type.

Number timestamp literals:
Seconds (10 digits), e.g. @1234567890
Milliseconds (13 digits), e.g. @1234567890123
Microseconds (16 digits), e.g. @1234567890123456
Nanoseconds (19 digits), e.g. @1234567890123456789
String timestamp literals:
ISO 8601 dates, e.g. `@'2023-08-07'
ISO 8601 date/time, e.g. @'2023-08-07T19:06:42'
ISO 8601 date/time with time zone, e.g. @'2023-08-07T19:06:42+03:00'
Dynamic expressions:
Numbers are interpreted as nanoseconds, e.g. @($d.ts_millis * 1000000).
Strings are parsed to a timestamp on a best-effort basis, e.g. @`2023-08-{$d.day}`. For extended and customizable timestamp parsing, see parseTimestamp.
A timestamp expression of any other data type returns null.
Interval Literals
An interval literal represents a span of time in a normalized and human-readable format, NdNhNmNsNmsNusNns where N is the amount of each time unit. The following rules apply:

It consists of time unit components - a non-negative integer followed by the short time unit name. Supported time units are: d, h, m, s, ms, us, ns.
There must be at least one time unit component.
The same time unit cannot appear more than once.
Components must be decreasing in time unit order - from days to nanoseconds.
It can start with - to represent negative intervals.
Regular Expression Literals
Expressions surrounded by / are regular expression literals.

The exact dialect of regular expression is dependent on the type of the query. If it is an archive query, the dialect supported is Ruby. If it is a frequent search query, the dialect supported is Lucene.

Examples:

/foo/
/[a-z]+/
/\/foo/
Timestamp Math
In addition to timestamp expressions and interval literals, Dataprime supports math operations between them:

timestamp + interval: adds an interval to a timestamp
timestamp - interval: subtracts an interval from a timestamp
timestamp - timestamp: calculates the interval between two timestamps
timestamp / interval: rounds a timestamp to the nearest interval
interval + interval: adds two intervals together
interval - interval: subtracts one interval from another
interval * number: multiplies an interval by a numeric factor
Scalar Functions
Various functions can be used to transform values. All functions can be called as methods as well, e.g. $d.msg.contains('x') is equivalent to contains($d.msg,'x').

String Functions
byteLength
byteLength(string: string): number

Returns the size of the string encoded as UTF-8

chr
chr(number: number): string

Returns the Unicode code point number as a single character string.

codepoint
codepoint(string: string): number

Returns the Unicode code point of the only character of string.

concat
concat(value: string, ...values: string): string

Concatenates multiple strings into one.

contains
contains(string: string, substring: string): bool

Returns true if substring is contained in string

endsWith
endsWith(string: string, suffix: string): bool

Returns true if string ends with suffix

indexOf
indexOf(string: string, substring: string): number

Returns the position of substring in string, or null if not found.

length
length(value: string): number

Returns the length of value

ltrim
ltrim(value: string): string

Removes whitespace to the left of the string value

matches
matches(string: string, regexp: regexp): bool

Evaluates the regular expression pattern and determines if it is contained within string.

pad
Alias for padLeft

pad(value: string, charCount: number, fillWith: string): string

Left pads string to charCount. If size < fillWith.length() of string, result is truncated. See padLeft for more details.

padLeft
padLeft(value: string, charCount: number, fillWith: string): string

Left pads string to charCount. If size < fillWith.length() of string, result is truncated.

padRight
padRight(value: string, charCount: number, fillWith: string): string

Right pads string to charCount. If size < fillWith.length() of string, result is truncated.

regexpSplitParts
regexpSplitParts(string: string, delimiter: regexp, index: number): string

Splits string on regexp-delimiter, returns the field at index. Indexes start with 1.

rtrim
rtrim(value: string): string

Removes whitespace to the right of the string value

splitParts
splitParts(string: string, delimiter: string, index: number): string

Splits string on delimiter, returns the field at index. Indexes start with 1.

startsWith
startsWith(string: string, prefix: string): bool

Returns true if string starts with prefix

substr
substr(value: string, from: number, length: number?): string

Returns the substring in value, from position from and up to length length

textSearch
textSearch(target: T, phrase: string): bool

Searches for the provided text phrase in the target value.

Function parameters:

target - the target to search in. The behaviour depends on the value's type:
primitive types such as string, number and bool are converted to strings;
text search in object succeeds when at least one of the values matches (not the keys);
text search in array succeeds when at least one of the elements matches;
phrase - the text phrase to search for. The value is tokenized and the tokens must appear in sequence in the target (that means in the same order and without other tokens inbetween). Must be a literal.
toLowerCase
toLowerCase(value: string): string

Converts value to lowercase

toUpperCase
toUpperCase(value: string): string

Converts value to uppercase

trim
trim(value: string): string

Removes whitespace from the edges of a string value

IP Functions
ipInRange
ipInRange(ip: string, startIp: string, endIp: string): bool

Returns true if ip is in the range of startIp and endIp.

ipInSubnet
ipInSubnet(ip: string, ipPrefix: string): bool

Returns true if ip is in the subnet of ipPrefix.

ipPrefix
ipPrefix(ip: string, subnetSize: number): string

Returns the IP prefix of a given ip_address with subnetSize bits (e.g.: 192.128.0.0/9).

UUID functions
isUuid
isUuid(uuid: string): bool

Returns true if uuid is valid.

randomUuid
randomUuid(): string

Returns a random UUIDv4.

uuid
Deprecated: use randomUuid instead

uuid(): string

Returns a random UUIDv4. See randomUuid for more details.

General functions
firstNonNull
firstNonNull(value: T, ...values: T): T

Returns the first non-null value from the parameters. Works only on scalars for now.

if
if(condition: bool, then: T, else: T?): T

return either the then or else according to the result of condition

in
in(comparand: T, value: T, ...values: T): bool where T in [string or bool or number or interval or timestamp or regexp or enum]

Tests if the comparand is equal to any of the values in a set v1 ... vN.

recordLocation
recordLocation(): string

Returns the location of the record (e.g.: s3 URL)

Number functions
abs
abs(number: number): number

Returns the absolute value of number

ceil
ceil(number: number): number

Rounds the value up to the nearest integer

e
e(): number

Returns the constant Euler’s number.

floor
floor(number: number): number

Rounds the value down to the nearest integer

fromBase
fromBase(string: string, radix: number): number

Returns the value of string interpreted as a base-radix number.

ln
ln(number: number): number

Returns the natural log of number

log
log(base: number, number: number): number

Returns the log of number in base base

log2
log2(number: number): number

Returns the log of number in base 2. Equivalent to log(2, number)

max
max(value: number, ...values: number): number

Returns the largest number of all the numbers passed to the function

min
min(value: number, ...values: number): number

Returns the smallest number of all the numbers passed to the function

mod
mod(number: number, divisor: number): number

Returns the modulus (remainder) of number divided by divisor.

pi
pi(): number

Returns the constant Pi.

power
power(number: number, exponent: number): number

Returns number^exponent

random
random(): number

Returns a pseudo-random value in the range 0.0 <= x < 1.0.

randomInt
randomInt(upperBound: number): number

Returns a pseudo-random integer number between 0 and n (exclusive)

round
round(number: number, digits: number?): number

Round number to digits decimal places

sqrt
sqrt(number: number): number

Returns square root of a number.

toBase
toBase(number: number, radix: number): string

Returns the base-radix representation of number.

URL functions
urlDecode
urlDecode(string: string): string

Unescapes the URL encoded in string.

urlEncode
urlEncode(string: string): string

Escapes string by encoding it so that it can be safely included in URL.

Date/Time functions
Functions for processing timestamps, intervals and other time-related constructs.

Time Units
Many date/time functions accept a time unit argument to tweak their behaviour. Dataprime supports time units from nanoseconds to days. They are represented as literal strings of the time unit name in either long or short notation:

long notation: 'day', 'hour', 'minute', 'second', 'milli', 'micro', 'nano'
short notation: 'd', 'h', 'm', 's', 'ms', 'us', 'ns'
Time Zones
Dataprime timestamps are always stored in the UTC time zone, but some date/time functions accept a time zone argument to tweak their behaviour. Time zone arguments are strings that specify a time zone offset, shorthand or identifier:

time zone offset in hours (e.g. '+01' or '-02')
time zone offset in hours and minutes (e.g. '+0130' or '-0230')
time zone offset in hours and minutes with separator (e.g. '+01:30' or '-02:30')
time zone shorthand (e.g. 'UTC', 'GMT', 'EST', etc.)
time zone identifier (e.g. 'Asia/Yerevan', 'Europe/Zurich', 'America/Winnipeg', etc.)
addInterval
addInterval(left: interval, right: interval): interval

Adds two intervals together. Works also with negative intervals. Equivalent to left + right.

addTime
addTime(t: timestamp, i: interval): timestamp

Adds an interval to a timestamp. Works also with negative intervals. Equivalent to t + i.

diffTime
diffTime(to: timestamp, from: timestamp): interval

Calculates the duration between two timestamps. Positive if to > from, negative if to < from. Equivalent to to - from.

divideInterval
divideInterval(i: interval, divisor: number): interval

Divides an interval by a number. Works both with integer and fractional numbers. Equivalent to i / divisor

extractTime
extractTime(timestamp: timestamp, unit: dateunit | timeunit, tz: string?): number

Extracts either a date or time unit from a timestamp. Returns a floating point number for time units smaller than a 'minute', otherwise an integer. Date units such as 'month' or 'week' start from 1 (not from 0).

Function parameters:

timestamp (required) - the timestamp to extract from.
unit (required) - the date or time unit to extract. Must be a string literal and one of:
any time unit in either long or short notation
a date unit in long notation: 'year', 'month', 'week', 'day_of_year', 'day_of_week'
a date unit in short notation: 'Y', 'M', 'W', 'doy', 'dow'
tz (optional) - a time zone to convert the timestamp before extracting.
# Example 1: extract the hour in Tokyo
limit 1 | choose $m.timestamp.extractTime('h', 'Asia/Tokyo') as h
# Result 1: 11pm
{ "h": 23 }

# Example 2: extract the number of seconds
limit 1 | choose $m.timestamp.extractTime('second') as s
# Result 2: 38.35 seconds
{ "s": 38.3510265 }

# Example 3: extract the timestamp's month
limit 1 | choose $m.timestamp.extractTime('month') as m
# Result 3: August
{ "m": 8 }

# Example 4: extract the day of the week
limit 1 | choose $m.timestamp.extractTime('dow') as d
# Result 4: Tuesday
{ "d": 2 }
formatInterval
formatInterval(interval: interval, scale: timeunit?): string

Formats interval to a string with an optional time unit scale.

Function parameters:

interval (required) - the interval to format.
scale (optional) - the largest time unit of the interval to show. Defaults to nano.
# Example:
limit 3 | choose formatInterval(now() - $m.timestamp, 's') as i
# Results:
{ "i": "122s261ms466us27ns"  }
{ "i": "122s359ms197us227ns" }
{ "i": "122s359ms197us227ns" }
formatTimestamp
formatTimestamp(timestamp: timestamp, format: string?, tz: string?): string

Formats a timestamp to a string with an optional format specification and destination time zone.

Function parameters:

timestamp (required) - the timestamp to format.
format (optional) - a date/time format specification for parsing timestamps. The following format options are supported:
'auto' (default) - alias for 'iso8601'
'iso8601' / 'iso8601bare' - ISO 8601 format with / without a time zone resp.
'timestamp_second' / 'timestamp_milli' / 'timestamp_micro' / 'timestamp_nano' - timestamp in seconds / milliseconds / microseconds / nanoseconds (10/13/16/19 digits) resp.
Custom timestamp formats
tz (optional) - the destination time zone to convert the timestamp before formatting.
# Example 1: print a timestamp with default format and +5h offset
limit 1 | choose $m.timestamp.formatTimestamp(tz='+05') as ts
# Result 1:
{ "ts": "2023-08-29T19:08:37.405937400+0500" }

# Example 2: print only the year and month
limit 1 | choose $m.timestamp.formatTimestamp('%Y-%m') as ym
# Result 2:
{ "ym": "2023-08" }

# Example 3: print only the hours and minutes
limit 1 | choose $m.timestamp.formatTimestamp('%H:%M') as hm
# Result 3:
{ "hm": "14:11" }

# Example 4: print a timestamp in milliseconds (13 digits)
limit 1 | choose $m.timestamp.formatTimestamp('timestamp_milli') as ms
# Result 4:
{ "ms": "1693318678696" }
fromUnixTime
fromUnixTime(unixTime: number, timeUnit: timeunit?): timestamp

Converts a number of a specific time units since the UNIX epoch to a timestamp (in UTC). The UNIX epoch starts on January 1, 1970 - earlier timestamps are represented by negative numbers.

Function parameters:

unixTime (required) - the amount of time units to convert. Can be either positive or negative and will be rounded down to an integer.
timeUnit (optional) - the time units to convert. Defaults to 'milli'.
# Example:
limit 1 | choose fromUnixTime(1658958157515, 'ms') as ts
# Result:
{ "ts": 1658958157515000000 }
multiplyInterval
multiplyInterval(i: interval, factor: number): interval

Multiplies an interval by a numeric factor. Works both with integer and fractional numbers. Equivalent to i * factor

now
now(offset: interval?): timestamp

Returns the current time at query execution time. Stable across all rows and within the entire query, even when used multiple times. Nanosecond resolution if the runtime supports it, otherwise millisecond resolution.

Function parameters:

offset (optional) - an optional offset to add to the current time (can be negative).
# Example:
limit 3 | choose now() as now, now() - $m.timestamp as since
# Results:
{ "now": 1693312549105874700, "since": "14m954ms329us764ns" }
{ "now": 1693312549105874700, "since": "14m954ms329us764ns" }
{ "now": 1693312549105874700, "since": "14m960ms519us564ns" }
parseInterval
parseInterval(string: string): interval

Parses an interval from a string with format NdNhNmNsNmsNusNns where N is the amount of each time unit. Returns null when the input does not match the expected format. See interval literals for a complete specification.

# Example 1: parse a zero interval
limit 1 | choose '0s'.parseInterval() as i
# Result 1:
{ "i": "0ns" }

# Example 2: parse a positive interval
limit 1 | choose '1d48h0m'.parseInterval() as i
# Result 2:
{ "i": "3d" }

# Example 3: parse a negative interval
limit 1 | choose '-5m45s'.parseInterval() as i
# Result 3:
{ "i": "-5m45s" }
parseTimestamp
parseTimestamp(string: string, format: string?, tz: string?): timestamp

Parses a timestamp from string with an optional format specification and time zone override. Returns null when the input does not match the expected format.

Function parameters:

string (required) - the input from which the timestamp will be extracted.
format (optional) - a date/time format specification for parsing timestamps. The following format options are supported:
'auto' (default) - attempt to parse a timestamp on a best-effort basis
'iso8601' / 'iso8601bare' - ISO 8601 format with / without a time zone resp.
'timestamp_second' / 'timestamp_milli' / 'timestamp_micro' / 'timestamp_nano' - timestamp in seconds / milliseconds / microseconds / nanoseconds (10/13/16/19 digits) resp.
Custom timestamp formats
'format1|format2|...' - a cascade of formats to attempt in sequence
tz (optional) - a time zone override to convert the timestamp while parsing. This parameter will override any time zone present in the input. A time zone can be extracted from the string by using an appropriate format and omitting this parameter.
# Example 1: parse a date with the default format
limit 1 | choose '2023-04-05'.parseTimestamp() as ts
# Result 1:
{ "ts": 1680652800000000000 }

# Example 2: parse a date in US format
limit 1 | choose '04/05/23'.parseTimestamp('%D') as ts
# Result 2:
{ "ts": 1680652800000000000 }

# Example 3: parse date and time with units
limit 1 | choose '2023-04-05 16h07m'.parseTimestamp('%F %Hh%Mm') as ts
# Result 3:
{ "ts": 1680710820000000000 }

# Example 4: parse a timestamp in seconds (10 digits)
limit 1 | choose '1680710853'.parseTimestamp('timestamp_second') as ts
# Result 4:
{ "ts": 1680710853000000000 }
parseToTimestamp
Deprecated: use parseTimestamp instead

parseToTimestamp(string: string, format: string?, tz: string?): timestamp

Parses a timestamp from string with an optional format specification and time zone override. See parseTimestamp for more details.

roundInterval
roundInterval(interval: interval, scale: timeunit): interval

Rounds an interval to a time unit scale. Smaller time units will be zeroed out.

Function parameters:

interval (required) - the interval to round.
scale (required) - the largest time unit of the interval to keep.
# Example:
limit 1 | choose 2h5m45s.roundInterval('m') as i
# Result:
{ "i": "2h5m" }
roundTime
roundTime(date: timestamp, interval: interval): timestamp

Rounds a timestamp to the given interval. Useful for bucketing, e.g. rounding to 1h for hourly buckets. Equivalent to date / interval.

# Example:
groupby $m.timestamp.roundTime(1h) as bucket count() as n
# Results:
{ "bucket": "29/08/2023 15:00:00.000 pm", "n": 40653715 }
{ "bucket": "29/08/2023 14:00:00.000 pm", "n": 1779386  }
subtractInterval
subtractInterval(left: interval, right: interval): interval

Subtracts one interval from another. Equivalent to addInterval(left, -right) and left - right.

subtractTime
subtractTime(t: timestamp, i: interval): timestamp

Subtracts an interval from a timestamp. Equivalent to addTime(t, -i) and t - i.

timeRound
Deprecated: use roundTime instead

timeRound(date: timestamp, interval: interval): timestamp

Rounds a timestamp to the given interval. See roundTime for more details.

toInterval
toInterval(number: number, timeUnit: timeunit?): interval

Converts a number of specific time units to an interval. Works with both integer / floating point and positive / negative numbers.

Function parameters:

number (required) - the amount of time units to convert.
timeUnit (optional) - the time units to convert. Defaults to nano.
# Example 1: convert a floating point number
limit 1 | choose 2.5.toInterval('h') as i
# Result 1:
{ "i": "2h30m" }

# Example 2: convert an integer number
limit 1 | choose -9000.toInterval() as i
# Result 2:
{ "i": "-9us" }
toIso8601DateTime
Deprecated

toIso8601DateTime(timestamp: timestamp): string

Alias to formatTimestamp(timestamp, 'iso8601').

Formats timestamp to an ISO 8601 string with nanosecond output precision.

# Example:
limit 1 | choose $m.timestamp.toIso8601DateTime() as ts
# Result:
{ "ts": "2023-08-11T07:29:17.634Z" }
toUnixTime
toUnixTime(timestamp: timestamp, timeUnit: timeunit?): number

Converts timestamp to a number of specific time units since the UNIX epoch (in UTC). The UNIX epoch starts on January 1, 1970 - earlier timestamps are represented by negative numbers.

Function parameters:

timestamp (required) - the timestamp to convert.
timeUnit (optional) - the time units to convert to. Defaults to 'milli'.
# Example:
limit 1 | choose $m.timestamp.toUnixTime('hour') as hr
# Result:
{ "hr": 470363 }
Encoding/Decoding functions
decodeBase64
decodeBase64(value: string): string

Decode a base-64 encoded string

encodeBase64
encodeBase64(value: string): string

Encode a string into base-64

Array functions
arrayAppend
arrayAppend(array: array<T>, element: T): array<T>

Returns array with an appended element

arrayConcat
arrayConcat(array1: array<T>, array2: array<T>): array<T>

Returns array containing elements of array1 and array2

arrayContains
arrayContains(array: array<T>, element: T): bool where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns true if the array contains the provided element

arrayInsertAt
arrayInsertAt(array: array<T>, position: number, value: T): array<T>

Returns array with value inserted at the specified position

arrayJoin
arrayJoin(array: array<T>, delimiter: string): string where T in [string or bool or number or interval or timestamp or regexp or enum]

Joins the array to a string with the provided delimiter

arrayLength
arrayLength(array: array<any>): number

Returns the length of an array

arrayRemove
arrayRemove(array: array<T>, element: T): array<T> where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns array with all occurrences of the element removed

arrayRemoveAt
arrayRemoveAt(array: array<T>, position: number): array<T>

Returns array with removed element at the specified position

arrayReplaceAll
arrayReplaceAll(array: array<T>, value: T, newValue: T): array<T> where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns array with all given values replaced with new_values

arrayReplaceAt
arrayReplaceAt(array: array<T>, position: number, value: T): array<T>

Returns array with value replaced at the specified position

arraySort
arraySort(array: array<T>, desc: bool?, nullsFirst: bool?): array<T> where T in [number or bool or string or interval or timestamp or regexp]

Returns the input array sorted according to the provided arguments:

desc (optional) - when true, the array is sorted in reverse (descending) order. Must be a literal, defaults to false.
nullsFirst (optional) - when true, nulls are appear at the start of the output. Must be a literal, defaults to false.
arraySplit
arraySplit(string: string, delimiter: regexp | string): array<string>

Splits the string into parts on the provided delimiter

cardinality
cardinality(array: array<T>): number where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns the number of unique elements in the array

inArray
inArray(element: T, array: array<T>): bool where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns true if the element is in the provided array

isEmpty
isEmpty(array: array<any>): bool

Returns true if the array is empty

isSubset
isSubset(array1: array<T>, array2: array<T>): bool where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns true if array1 is a subset of array2 (disregarding duplicates).

isSuperset
isSuperset(array1: array<T>, array2: array<T>): bool where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns true if array1 is a superset of array2 (disregarding duplicates).

setDiff
setDiff(array1: array<T>, array2: array<T>): array<T> where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns the set difference of two arrays. It includes elements from array1 that are not in array2.

setDiffSymmetric
setDiffSymmetric(array1: array<T>, array2: array<T>): array<T> where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns the symmetric set difference of two arrays. It includes elements from either array1 or array2 but not both.

setEqualsTo
setEqualsTo(array1: array<T>, array2: array<T>): bool where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns true if array1 has the same elements as array2 (disregarding duplicates).

setIntersection
setIntersection(array1: array<T>, array2: array<T>): array<T> where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns the intersection of two arrays (treated as sets):

duplicates are removed
order is not preserved
null is treated as the empty set
setUnion
setUnion(array1: array<T>, array2: array<T>): array<T> where T in [string or bool or number or interval or timestamp or regexp or enum]

Returns the union of two arrays (treated as sets):

duplicates are removed
order is not preserved
null is treated as the empty set
Case expressions
Case expressions are special constructs in the language that allow choosing between multiple options in an easy manner and in a readable way. They can be wherever an expression is expected.

case
Choose between multiple values based on several generic conditions. Resort to a default-value if no condition is met.

case {
  condition1 -> value1,
  condition2 -> value2,
  ...
  conditionN -> valueN,
  _          -> <default-value>
}
Example:

case {
  $d.status_code == 200 -> 'success',
  $d.status_code == 201 -> 'created',
  $d.status_code == 404 -> 'not-found',
  _ -> 'other'
}

# Here's the same example inside the context of a query. A new field is created with the `case` result,
# and then a filter will be applied, leaving only non-successful responses.

source logs | ... | create $d.http_response_outcome from case {
  $d.status_code == 200 -> 'success',
  $d.status_code == 201 -> 'created',
  $d.status_code == 404 -> 'not-found',
  _                     -> 'other'
} | filter $d.http_response_outcome != 'success'
case_contains
A shorthand for case which allowing checking if a string s contains one of several substrings without repeating the expression leading to s. The chosen value is the first which matches s.contains(substring).

case_contains {
  s: string,
  substring1 -> result1,
  substring2 -> result2,
  ...
  substring3 -> resultN
}
Example:

case_contains {
  $l.subsystemname,
  '-prod-' -> 'production',
  '-dev-'  -> 'development',
  '-stg-'  -> 'staging',
  _        -> 'test'
}
case_equals
A shorthand for case which allowing comparing some expression e to several results without repeating the expression. The chosen value is the first which matches s == value

case_equals {
  e: any,
  value1 -> result1,
  value2 -> result2,
  ...
  valueN -> resultN
}
Example:

case_equals {
  $m.severity,
  'info'   -> true,
  'warning -> true,
  _        -> false
}
case_greaterthan
A shorthand for case which allows comparing n to multiple values without repeating the expression leading to n. The chosen value is the first which matches expression > value.

case_greaterthan {
  n: number,
  value1: number -> result1,
  value2: number -> result2,
  ...
  valueN: number -> resultN,
  _              -> <default-value>
}
Example:

case_greaterthan {
  $d.status_code,
  500 -> 'server-error',
  400 -> 'client-error',
  300 -> 'redirection',
  200 -> 'success',
  100 -> 'information',
  _   -> 'other'
}
case_lessthan
A shorthand for case which allows comparing a number n to multiple values without repeating the expression leading to n. The chosen value is the first which matches expression < value.

case_lessthan {
  n: number,
  value1: number -> result1,
  value2: number -> result2,
  ...
  valueN: number -> resultN,
  _              -> <default-value>
}
Example:

case_lessthan {
  $d.temperature_celsius,
  10 -> 'freezing',
  20 -> 'cold',
  30 -> 'fun',
  45 -> 'hot',
  _  -> 'burning'
}
Aggregation Functions
any_value
any_value(expression: T?): T

Returns any non-null expression value in the group. If expression is not defined, it defaults to the $d object.

Returns null if all expression values in the group are null.

Example:

groupby $m.severity aggregate any_value($d.url)
approx_count_distinct
approx_count_distinct(value: T, ...values: bool | enum | interval | number | regexp | string | timestamp): number where T in [string or bool or number or interval or timestamp or regexp or enum]

Calculates the approximate count of all distinct combinations of values. Does not compute an exact count, but is more efficient than distinct_count.

Example:

groupby $m.severity aggregate approx_count_distinct($d.field1, $d.field2, ...)
avg
avg(expression: number): number

Calculates the average value of a numerical expression in the group.

Example:

groupby $m.severity aggregate avg($d.duration) as average_duration
groupby $d.my.pod_name aggregate max($d.my.memory_usage) - avg($d.my.memory_usage) as avg_mem_range
collect
collect(expression: T, distinct: bool?, limit: number?, ignoreNulls: bool?): array<T>

Returns an array collecting all expression elements for each group.

Function parameters:

expression (required) - specifies the array elements to collect.
distinct (optional) - when true, collect only unique elements. Must be a literal, defaults to false.
limit (optional) - when provided, specifies the maximum number of elements to collect. Must be a positive literal number.
ignoreNulls (optional) - when true, discard null elements. Must be a literal, defaults to false.
Examples:

# Collect all distinct containers per application.
groupby $l.applicationname aggregate collect(kubernetes.container_name, distinct = true)
# Collect up to 100 pod names per application.
groupby $l.applicationname aggregate collect(kubernetes.pod_name, limit = 100)
# Collect all log IDs in a file.
groupby recordLocation() aggregate collect($m.logid)
# Collect all non-null error messages.
groupby transaction_id aggregate collect(error.message, ignoreNulls = true)
count
count(expression: T?): number

Counts non-null expression values. If expression is not defined, all rows will be counted.

An alias can be provided to override the keypath the result will be written to.

For example, the following part of a query

count() into $d.num_rows
will result in a single row of the following form:

{ "num_rows": 7532 }
Example:

groupby $m.severity aggregate count() * 2
count_if
count_if(condition: bool, expression: T?): number

Counts non-null expression values on rows which satisfy condition. If expression is not defined, all rows that satisfy condition will be counted.

Example:

groupby $m.severity aggregate count_if($d.duration > 500) as $d.high_duration_logs
groupby $m.severity aggregate count_if($d.duration > 500, $d.company_id) as $d.high_duration_logs
distinct_count
distinct_count(expression: T): number where T in [string or bool or number or interval or timestamp or regexp or enum]

Counts non-null distinct expression values.

Example:

groupby $l.applicationname aggregate distinct_count($d.username) as active_users
distinct_count_if
distinct_count_if(condition: bool, expression: T): number where T in [string or bool or number or interval or timestamp or regexp or enum]

Counts non-null distinct expression values on rows which satisfy condition.

Example:

groupby $l.applicationname aggregate distinct_count_if($m.severity == 'Error', $d.username) as users_with_errors
max
max(expression: T): T where T in [number or bool or string or interval or timestamp or regexp]

Calculates the maximum value of a numerical expression in the group.

Example:

groupby $m.severity aggregate max($d.duration)
groupby $m.severity aggregate max($d.my.minute) - min($d.my.minute)
max_by
max_by(sortKey: T, expression: U): U where T in [number or bool or string or interval or timestamp or regexp]

Calculates the maximum value of expression for each sort key.

Examples:

# Input
{ "session_id": "abc", "snapshot_num": 1, "failed": false, "os": "Linux" }
{ "session_id": "abc", "snapshot_num": 2, "failed": true, "os": "Linux" }
{ "request_id": "xyz", "snapshot_num": 0, "failed": false, "os": "MacOS" }

source logs | groupby session_id agg
  max(snapshot_num) as snapshot,
  max_by(snapshot_num, failed) as failed,
  max_by(snapshot_num, os) as os

# Result Structure
{
  "session_id": "abc",
  "snapshot": 2,
  "failed": true,
  "os": "Linux"
}
{
  "session_id": "xyz",
  "snapshot": 0,
  "failed": false,
  "os": "MacOS"
}
min
min(expression: T): T where T in [number or bool or string or interval or timestamp or regexp]

Calculates the minimum value of a numerical expression in the group.

Example:

groupby $m.severity aggregate min($d.duration)
min_by
min_by(sortKey: T, expression: U): U where T in [number or bool or string or interval or timestamp or regexp]

Calculates the minimum value of expression for each sort key.

Examples:

# Input
{ "session_id": "abc", "snapshot_num": 1, "failed": false, "os": "Linux" }
{ "session_id": "abc", "snapshot_num": 2, "failed": true, "os": "Linux" }
{ "request_id": "xyz", "snapshot_num": 0, "failed": false, "os": "MacOS" }

source logs | groupby session_id agg
  min(snapshot_num) as snapshot,
  min_by(snapshot_num, failed) as failed,
  min_by(snapshot_num, os) as os

# Result Structure
{
  "session_id": "abc",
  "snapshot": 1,
  "failed": false,
  "os": "Linux"
}
{
  "session_id": "xyz",
  "snapshot": 0,
  "failed": false,
  "os": "MacOS"
}
percentile
percentile(percentile: number, expression: number, errorThreshold: number?): number

Calculates the approximate n-th percentile value of a numerical expression in the group.

Since the percentile calculation is approximate, the accuracy may be controlled with the errorThreshold parameter which ranges from 0 to 1 (defaults to 0.01). A lower value will result in better accuracy at the cost of longer query times.

Example:

groupby $m.severity aggregate percentile(0.99, $d.duration) as p99_latency
groupby $m.severity aggregate percentile(0.75, $d.duration) - percentile(0.25, $d.duration) as percentile_range
sample_stddev
sample_stddev(expression: number): number

Computes the sample standard deviation of a numerical expression in the group.

Example:

groupby $m.severity aggregate sample_stddev($d.duration)
sample_variance
sample_variance(expression: number): number

Computes the variance of a numerical expression in the group.

Example:

groupby $m.severity aggregate sample_variance($d.duration)
stddev
stddev(expression: number): number

Computes the standard deviation of a numerical expression in the group.

Example:

groupby $m.severity aggregate stddev($d.duration)
sum
sum(expression: number): number

Calculates the sum of a numerical expression in the group.

Example:

groupby $m.severity aggregate sum($d.duration) as total_duration
variance
variance(expression: number): number

Computes the variance of a numerical expression in the group.

Example:

groupby $m.severity aggregate variance($d.duration)
Extractor Functions
jsonobject
jsonobject([<max_unescape_count>])

Extracts an object from a string containing an encoded json object, potentially unescaping the string before decoding it into a json.

Function parameters:

max_unescape_count - Max number of escaping levels to unescape before parsing the json, defaults to 1. When set to 1 or more, the engine will detect whether the value contains an escaped JSON string and unescape it until its parsable or max unescape count is exceeded.
Example:

e $d.json_message_as_str into $d.json_message using jsonobject(max_unescape_count=1)
kv
kv([<pair_delimiter_string>][, <key_delimiter_string>][, <quote_char_value>])

Extracts an object from a string containing key=value pairs.

Function parameters:

pair_delimiter - The delimiter to expect between pairs. Defaults to (a space)
key_delimiter - The delimiter to expect separating between a key and a value. Defaults to =.
quote_char_value - The character to expect as a quote for the value. Defaults to ".
Examples:

extract $d.text into $d.my_kvs using kv()
e $d.text into $d.my_kvs using kv(pair_delimiter=' ',key_delimiter='=')
multi_regexp
multi_regexp(e=/<regexp>/)

Creates a new keypath containing an array with regexp matches.

Function parameters:

e - A regular expression.
Example:

extract $d.my_string into $d.all_numbers using multi_regexp(/\d+/)
regexp
regexp(e=/<regexp>/)

Creates a new keypath containing an object with the capture groups. Note that regexp extractor will not overwrite an existing keypath.

Function parameters:

e - A regular expression with named capture groups.
Example:

extract $d.my_text into $d.my_data using regexp(e=/user (?<user>.*) has logged in/)
split
`split(delimiter=',',element_datatype=string)

Splits a string containing delimited data into a new array of primitive types.

Function parameters:

delimiter - The delimiter to expect between values.
element_datatype - The datatype of the elements to extract. string, number and bool are supported.
Example:

extract $d.message into $d.codes using split(',', number)