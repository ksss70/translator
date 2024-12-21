# Translator

## What is it?
translator is a CLI tool for converting configuration conf. files to toml with syntax error detection


## The syntax of the language to be converted
**Arrays**
```
#(value, value, value, ... ) 
```

**Dictionaries**
```
$[
    name: value,
    name: value,
    name: value
]
```

**Names**
```
[a-zA-Z][_a-zA-Z0-9]*
```

**Values**
- Arrays
- Numbers
- Dictionaries

**Declaring a constant**

```
def name := value
```

**Calculating the constant**

```
.{name}.
```

## Example of input file

```
[server]
host = "localhost"  
port = 8080
constants = { MAX_CONNECTIONS = 100, TIMEOUT = 30 }

```
