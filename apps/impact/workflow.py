STATUS=[('draft','Draft'),('submitted','Submitted'),('under_review','Under review'),('approved','Approved'),('rejected','Rejected'),('requires_correction','Requires correction')]
NEXT={'draft':{'submitted'},'requires_correction':{'submitted'},'submitted':{'under_review','approved','rejected','requires_correction'},'under_review':{'approved','rejected','requires_correction'}}
NEED_NOTE={'rejected','requires_correction'}
EDITABLE={'draft','requires_correction'}
def allowed(frm,to): return to in NEXT.get(frm,set())
