# type: ignore # noqa
# fmt: off
_m='dependentSchemas'
_l='dependentRequired'
_k='maxContains'
_j='minContains'
_i='patternProperties'
_h='properties'
_g='uniqueItems'
_f='$id'
_e='else'
_d='then'
_c='not'
_b='oneOf'
_a='anyOf'
_Z='allOf'
_Y='pattern'
_X='contains'
_W='propertyNames'
_V='additionalProperties'
_U='required'
_T='items'
_S='prefixItems'
_R='maxItems'
_Q='minItems'
_P='type'
_O='maxProperties'
_N='minProperties'
_M='maxLength'
_L='minLength'
_K='multipleOf'
_J='exclusiveMaximum'
_I='exclusiveMinimum'
_H='maximum'
_G='minimum'
_F='enum'
_E='const'
_D='number'
_C=True
_B=False
_A=None
_imp = lambda n,s: (m := __import__(n, fromlist=[""]), {i: getattr(m, i) for i in s})[-1]
_imp2 = lambda n,s: (m := __import__(n, fromlist=[""]), {s: m})[-1]
globals().update(**_imp('typing',['Any','NamedTuple']), **_imp('urllib.parse',['unquote','urldefrag','urljoin']), **_imp2('regex','re'), **_imp('decimal',['Decimal','InvalidOperation']))
SchemaError = type('SchemaError', (Exception,), {})
ValidationError = type('ValidationError', (Exception,), {})
ValidationResult = type("ValidationResult",(),{"__init__": lambda A,B=_A,C=_A: vars(A).update(evaluated_properties=set(B or()), evaluated_items=set(C or())),"merge": lambda A,o: (A.evaluated_properties.update(o.evaluated_properties), A.evaluated_items.update(o.evaluated_items), A)[-1] if o is not _A else A,})
class SchemaRegistry:
	def __init__(A,documents=_A,loaders=_A):
		A._documents={};A._loaders=list(loaders or())
		for(B,C)in(documents or{}).items():A.register(B,C)
	def register(B,uri,document):A=document;B._documents[uri]=A;collect_schema_resources(A,uri,B);return A
	def add_loader(A,loader):A._loaders.append(loader)
	def resolve_document(B,uri):
		A=uri
		if A in B._documents:return B._documents[A]
		for D in B._loaders:
			C=D(A)
			if C is not _A:return B.register(A,C)
		sfail(f"Schema URI could not be resolved: {A}")
	def get(A,uri):return A._documents.get(uri)
def fail(message):raise ValidationError(message)
def sfail(message):raise SchemaError(message)
def json_equal(a,b):
	if isinstance(a,bool)or isinstance(b,bool):return type(a)is type(b)and a==b
	if isinstance(a,(int,float))and isinstance(b,(int,float)):return a==b
	if type(a)is not type(b):return _B
	if isinstance(a,list):return len(a)==len(b)and all(json_equal(A,B)for(A,B)in zip(a,b))
	if isinstance(a,dict):return a.keys()==b.keys()and all(json_equal(a[A],b[A])for A in a)
	return a==b
def validate_type(data,schema,schema_context=_A):
	C=schema;B=data
	if _P not in C:return
	A=C[_P]
	if isinstance(A,list):
		if any(matches_type(B,A)for A in A):return
		fail(f"Expected one of {A}, got {type(B).__name__}");return
	if not matches_type(B,A):fail(f"Expected {A}, got {type(B).__name__}")
def match_integer(data):A=data;return isinstance(A,int)and not isinstance(A,bool)or isinstance(A,float)and A.is_integer()
def matches_type(data,expected):
	B=expected;A=data
	match B:
		case'null':return A is _A
		case'boolean':return isinstance(A,bool)
		case'object':return isinstance(A,dict)
		case'array':return isinstance(A,list)
		case'integer':return match_integer(A)
		case'number':return isinstance(A,(int,float))and not isinstance(A,bool)
		case'string':return isinstance(A,str)
		case _:fail(f"Unknown type: {B}")
def validate_const(data,schema,schema_context=_A):
	A=schema
	if _E in A and not json_equal(data,A[_E]):fail(f"Expected const {A[_E]!r}")
def validate_enum(data,schema,schema_context=_A):
	A=schema
	if _F in A and not any(json_equal(data,A)for A in A[_F]):fail(f"Expected one of {A[_F]!r}")
def validate_number_minimum(data,schema,schema_context=_A):
	B=schema;A=data
	if not matches_type(A,_D):return
	if _G in B and A<B[_G]:fail(f"{A} is less than minimum {B[_G]}")
def validate_number_maximum(data,schema,schema_context=_A):
	B=schema;A=data
	if not matches_type(A,_D):return
	if _H in B and A>B[_H]:fail(f"{A} is greater than maximum {B[_H]}")
def validate_number_exclusive_minimum(data,schema,schema_context=_A):
	B=schema;A=data
	if not matches_type(A,_D):return
	if _I in B and A<=B[_I]:fail(f"{A} is not greater than exclusiveMinimum {B[_I]}")
def validate_number_exclusive_maximum(data,schema,schema_context=_A):
	B=schema;A=data
	if not matches_type(A,_D):return
	if _J in B and A>=B[_J]:fail(f"{A} is not less than exclusiveMaximum {B[_J]}")
def validate_number_multiple_of(data,schema,schema_context=_A):
	B=schema;A=data
	if not matches_type(A,_D):return
	if _K not in B:return
	try:
		A=Decimal(str(A));C=Decimal(str(B[_K]))
		if C==0:fail('multipleOf cannot be zero')
		if A%C!=0:fail(f"{A} is not multipleOf {C}")
	except InvalidOperation:fail(f"{A} is not multipleOf {B[_K]}")
def validate_string_min_length(data,schema,schema_context=_A):
	A=schema
	if not isinstance(data,str):return
	if _L in A and len(data)<A[_L]:fail(f"String too short, minimum length {A[_L]}")
def validate_string_max_length(data,schema,schema_context=_A):
	A=schema
	if not isinstance(data,str):return
	if _M in A and len(data)>A[_M]:fail(f"String too long, maximum length {A[_M]}")
def validate_array_min_items(data,schema,schema_context=_A):
	A=schema
	if not isinstance(data,list):return
	if _Q in A and len(data)<A[_Q]:fail('Array too short')
def validate_array_max_items(data,schema,schema_context=_A):
	A=schema
	if not isinstance(data,list):return
	if _R in A and len(data)>A[_R]:fail('Array too long')
def validate_array_unique_items(data,schema,schema_context=_A):
	A=data
	if not isinstance(A,list):return
	if schema.get(_g)is _C:
		for B in range(len(A)):
			for C in range(B+1,len(A)):
				if json_equal(A[B],A[C]):fail('Array items are not unique')
def validate_array_items(data,schema,schema_context=_A):
	G=schema_context;B=schema;A=data
	if not isinstance(A,list):return ValidationResult()
	C=ValidationResult();D=0
	if _S in B:
		H=B[_S]
		for(E,F)in enumerate(H):
			if E<len(A):validate_json(A[E],F,G);C.evaluated_items.add(E)
		D=len(H)
	if _T in B:
		F=B[_T]
		for(I,J)in enumerate(A[D:],start=D):validate_json(J,F,G);C.evaluated_items.add(I)
	return C
def validate_object_required(data,schema,schema_context=_A):
	A=schema
	if not isinstance(data,dict):return
	if _U in A:
		for B in A[_U]:
			if B not in data:fail(f"Missing required property: {B}")
def validate_object_properties(data,schema,schema_context=_A):
	E=schema_context;C=data;B=schema
	if not isinstance(C,dict):return ValidationResult()
	D=ValidationResult()
	if _N in B:
		if len(C)<B[_N]:fail(f"Object has {len(C)} properties, minimum is {B[_N]}")
	if _O in B:
		if len(C)>B[_O]:fail(f"Object has {len(C)} properties, maximum is {B[_O]}")
	J=B.get(_h,{});K=B.get(_i,{});L=_V in B;F=B.get(_V,_C);G=set()
	for(A,H)in J.items():
		if A in C:validate_json(C[A],H,E);G.add(A);D.evaluated_properties.add(A)
	for(M,H)in K.items():
		N=re.compile(M)
		for(A,I)in C.items():
			if N.search(A):validate_json(I,H,E);G.add(A);D.evaluated_properties.add(A)
	for(A,I)in C.items():
		if A in G:continue
		if F is _C:
			if L:D.evaluated_properties.add(A)
			continue
		if F is _B:fail(f"Additional property '{A}' is not allowed")
		validate_json(I,F,E);D.evaluated_properties.add(A)
	return D
def validate_property_names(data,schema,schema_context=_A):
	A=schema
	if not isinstance(data,dict):return
	if _W not in A:return
	B=A[_W]
	for C in data:validate_json(C,B,schema_context)
def validate_array_contains(data,schema,schema_context=_A):
	C=schema_context;A=schema
	if not isinstance(data,list):return ValidationResult()
	if _X not in A:return ValidationResult()
	E=C.root if C else A;F=ValidationResult();B=0
	for(H,I)in enumerate(data):
		try:validate_json(I,A[_X],schema_context=C._replace(root=E)if C else SchemaContext(root=E,registry=SchemaRegistry()));B+=1;F.evaluated_items.add(H)
		except ValidationError:pass
	G=A.get(_j,1);D=A.get(_k)
	if B<G:fail(f"contains matched {B}, expected at least {G}")
	if D is not _A and B>D:fail(f"contains matched {B}, expected at most {D}")
	return F
def _regex_compile(pattern):
	A=pattern
	try:return re.compile(A)
	except re.error as B:sfail(f"Invalid regex pattern {A!r}: {B}")
def pattern_matches(data,pattern,schema_context=_A):
	if not isinstance(data,str):return _B
	return _regex_compile(pattern).search(data)is not _A
def validate_string_pattern(data,schema,schema_context=_A):
	A=schema
	if not isinstance(data,str):return
	if _Y in A:
		B=A[_Y]
		if not pattern_matches(data,B,schema_context):fail(f"String does not match pattern {B!r}")
def validate_allof(data,schema,schema_context=_A):
	A=schema;B=ValidationResult()
	if _Z in A:
		for C in A[_Z]:B.merge(validate_json(data,C,schema_context))
	return B
def validate_anyof(data,schema,schema_context=_A):
	A=schema;B=ValidationResult()
	if _a in A:
		C=0
		for D in A[_a]:
			try:B.merge(validate_json(data,D,schema_context));C+=1
			except ValidationError:continue
		if C==0:fail("Data does not match any of the 'anyOf' schemas")
	return B
def validate_oneof(data,schema,schema_context=_A):
	B=schema;C=ValidationResult()
	if _b in B:
		A=0
		for D in B[_b]:
			try:E=validate_json(data,D,schema_context);A+=1;C=E
			except ValidationError:continue
		if A!=1:fail(f"Data matches {A} schemas in 'oneOf', expected exactly one")
	return C
def validate_not(data,schema,schema_context=_A):
	A=schema
	if _c in A:
		if _is_json_valid(data,A[_c],schema_context):fail("Data matches the 'not' schema, which is not allowed")
def validate_conditional(data,schema,schema_context=_A):
	D=schema_context;C=data;A=schema;B=ValidationResult()
	if'if'not in A:return B
	try:E=validate_json(C,A['if'],D);F=_C
	except ValidationError:E=ValidationResult();F=_B
	if F:
		B.merge(E)
		if _d in A:B.merge(validate_json(C,A[_d],D))
	elif _e in A:B.merge(validate_json(C,A[_e],D))
	return B
def validate_dependent_required(data,schema,schema_context=_A):
	A=data
	if not isinstance(A,dict):return
	B=schema.get(_l)
	if B is _A:return
	for(C,E)in B.items():
		if C not in A:continue
		for D in E:
			if D not in A:fail(f"Property {C!r} requires property {D!r}")
def validate_dependent_schemas(data,schema,schema_context=_A):
	A=data
	if not isinstance(A,dict):return ValidationResult()
	B=schema.get(_m)
	if B is _A:return ValidationResult()
	C=ValidationResult()
	for(D,E)in B.items():
		if D in A:C.merge(validate_json(A,E,schema_context))
	return C
def validate_unevaluated_properties(data,schema,schema_context,current_result):
	D='unevaluatedProperties';A=schema
	if not isinstance(data,dict)or D not in A:return ValidationResult()
	B=ValidationResult();E=A[D]
	for(C,F)in data.items():
		if C in current_result.evaluated_properties:continue
		validate_json(F,E,schema_context);B.evaluated_properties.add(C)
	return B
def validate_unevaluated_items(data,schema,schema_context,current_result):
	D='unevaluatedItems';A=schema
	if not isinstance(data,list)or D not in A:return ValidationResult()
	B=ValidationResult();E=A[D]
	for(C,F)in enumerate(data):
		if C in current_result.evaluated_items:continue
		validate_json(F,E,schema_context);B.evaluated_items.add(C)
	return B
KEYWORDS_TO_VALIDATE={_P:validate_type,_E:validate_const,_F:validate_enum,_G:validate_number_minimum,_H:validate_number_maximum,_I:validate_number_exclusive_minimum,_J:validate_number_exclusive_maximum,_K:validate_number_multiple_of,_L:validate_string_min_length,_M:validate_string_max_length,_Q:validate_array_min_items,_R:validate_array_max_items,_g:validate_array_unique_items,(_S,_T):validate_array_items,_U:validate_object_required,(_h,_i,_V,_O,_N):validate_object_properties,_W:validate_property_names,(_X,_k,_j):validate_array_contains,_Y:validate_string_pattern,_Z:validate_allof,_a:validate_anyof,_b:validate_oneof,_c:validate_not,('if',_d,_e):validate_conditional,_l:validate_dependent_required,_m:validate_dependent_schemas}
def parse_external_ref(ref,base_uri=''):A=urljoin(base_uri,ref);B,C=urldefrag(A);return B,C
def unescape_json_pointer(pointer):return re.sub('~1','/',re.sub('~0','~',pointer))
def resolve_json_pointer(schema,fragment):
	D=schema;A=fragment;A=unquote(A)
	if A=='':return D
	if not A.startswith('/'):sfail(f"Invalid JSON Pointer '{A}'")
	E=A.lstrip('/').split('/');B=D
	for C in E:
		C=unescape_json_pointer(C)
		if isinstance(B,list):
			try:F=int(C);B=B[F]
			except(ValueError,IndexError):sfail(f"Invalid array index '{C}' in JSON Pointer '{A}'")
		elif isinstance(B,dict):
			if C not in B:sfail(f"Key '{C}' not found in JSON Pointer '{A}'")
			B=B[C]
		else:sfail(f"Cannot traverse into non-container type at '{C}' in JSON Pointer '{A}'")
	return B
def find_anchor(schema,anchor_name):
	B=anchor_name;A=schema
	if isinstance(A,dict):
		if A.get('$anchor')==B or A.get('$dynamicAnchor')==B:return A
		for C in A.values():
			try:return find_anchor(C,B)
			except SchemaError:pass
	elif isinstance(A,list):
		for D in A:
			try:return find_anchor(D,B)
			except SchemaError:pass
	sfail(f"Anchor not found: {B}")
def resolve_ref(ref,schema_context):
	B=schema_context;E,C=parse_external_ref(ref,B.base_uri)
	if E in('',_A):A=B.root;D=B.base_uri
	else:A=B.registry.resolve_document(E);D=E
	if C.startswith('/'):return ResolvedRef(resolve_json_pointer(A,C),A,D)
	if C:return ResolvedRef(find_anchor(A,C),A,D)
	return ResolvedRef(A,A,D)
def validate_reference(json_data,ref,schema_context):B=schema_context;A=resolve_ref(ref,B);return validate_json(json_data,A.schema,B._replace(root=A.root,base_uri=A.base_uri))
class SchemaContext(NamedTuple):root:Any;registry:SchemaRegistry;base_uri:str=''
class ResolvedRef(NamedTuple):schema:Any;root:Any;base_uri:str
def collect_schema_resources(schema,base_uri,registry):
	C=registry;B=base_uri;A=schema
	if isinstance(A,dict):
		D=B;E=A.get(_f)
		if isinstance(E,str):D=urljoin(B,E);C._documents[D]=A
		for F in A.values():collect_schema_resources(F,D,C)
	elif isinstance(A,list):
		for G in A:collect_schema_resources(G,B,C)
def validate_json(json_data,schema,schema_context=_A,registry=_A):
	J='$dynamicRef';I='$ref';E=json_data;D=registry;B=schema_context;A=schema
	if A is _C:return ValidationResult()
	if A is _B:fail('Boolean schema false rejects everything')
	if not isinstance(A,dict):fail('Schema must be object or boolean')
	if B is _A:
		if D is _A:D=SchemaRegistry()
		elif not isinstance(D,SchemaRegistry):D=SchemaRegistry(documents=D)
		collect_schema_resources(A,'',D);B=SchemaContext(root=A,registry=D)
	if _f in A:
		if B.registry.get(B.base_uri)is A:F=B.base_uri
		else:F=urljoin(B.base_uri,A[_f])
		B=B._replace(base_uri=F);B.registry._documents[F]=A
	if I in A:C=ValidationResult().merge(validate_reference(E,A[I],B))
	else:C=ValidationResult()
	if J in A:C.merge(validate_reference(E,A[J],B))
	for(G,H)in KEYWORDS_TO_VALIDATE.items():
		if isinstance(G,tuple):
			if any(B in A for B in G):C.merge(H(E,A,B))
		elif G in A:C.merge(H(E,A,B))
	C.merge(validate_unevaluated_properties(E,A,B,C));C.merge(validate_unevaluated_items(E,A,B,C));return C
def _is_json_valid(json_data,schema,schema_context=_A,registry=_A):
	try:validate_json(json_data,schema,schema_context,registry=registry);return _C
	except ValidationError:return _B
def is_json_valid(json_data,schema,registry=_A):return _is_json_valid(json_data,schema,registry=registry)
