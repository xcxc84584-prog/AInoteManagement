"""Explicitly synchronized, isolated Local Explorer repository."""
from pathlib import Path
from local_backend import LocalDB,FIELDS
from local_service import pack,restore

def repository(state,mode,root,owner):
    key='_isolated_local_repository_'+str(owner)
    if mode=='sqlite':
        path=Path(root)/'local_repository'/'bv_local_repository.sqlite3'
        if key not in state or state[key].path!=str(path):state[key]=LocalDB(path)
    elif key not in state:
        state[key]=LocalDB() # Session-only: never use server filesystem for remote visitors
    return state[key]

def selected_ids(rows,nid):
    byid={str(r['id']):r for r in rows}
    if str(nid) not in byid:raise ValueError('找不到選取的文件')
    ids={str(nid)}
    changed=True
    while changed:
        old=len(ids)
        ids.update(str(r['id']) for r in rows if str(r.get('parent_id') or '') in ids)
        changed=len(ids)!=old
    return ids

def transfer(source,target,owner,nid):
    src=source.export_snapshot(owner); dst=target.export_snapshot(owner)
    ids=selected_ids(src['notes'],nid)
    # Preserve parent hierarchy in destination, as cloud single-file transfer does.
    index={str(r['id']):r for r in src['notes']}
    for ident in list(ids):
        parent=index[ident].get('parent_id')
        while parent and str(parent) in index:
            ids.add(str(parent));parent=index[str(parent)].get('parent_id')
    incoming={k:[] for k in FIELDS}
    incoming['notes']=[r for r in src['notes'] if str(r['id']) in ids]
    incoming['assets']=[r for r in src['assets'] if str(r.get('note_id')) in ids]
    for k in ('schedule_cards','daily_tasks','daily_task_checks'):incoming[k]=[]
    merged={k:list(dst[k]) for k in FIELDS}
    for k in ('notes','assets'):
        old={str(r['id']):r for r in merged[k]}
        for r in incoming[k]:old[str(r['id'])]=r
        merged[k]=list(old.values())
    merged['media']=dict(dst.get('media',{}))
    for a in incoming['assets']:
        p=a.get('storage_path')
        if p in src.get('media',{}):merged['media'][p]=src['media'][p]
    target.import_snapshot(owner,merged,replace=True)
    return {'files':len(incoming['notes']),'assets':len(incoming['assets'])}


def delete_subtree(db,owner,nid):
    """Delete only from the isolated repository, including descendants and orphaned media."""
    snap=db.export_snapshot(owner)
    ids=selected_ids(snap['notes'],nid)
    snap['notes']=[r for r in snap['notes'] if str(r['id']) not in ids]
    removed_assets=[a for a in snap['assets'] if str(a.get('note_id')) in ids]
    snap['assets']=[a for a in snap['assets'] if str(a.get('note_id')) not in ids]
    used_paths={a.get('storage_path') for a in snap['assets']}
    removed_paths={a.get('storage_path') for a in removed_assets}-used_paths
    for path in removed_paths:snap['media'].pop(path,None)
    db.import_snapshot(owner,snap,replace=True)
    # LocalDB media entries are managed in its SQLite media table.
    if removed_paths:
        with db.lock,db.conn:
            for path in removed_paths:
                db.conn.execute('DELETE FROM media WHERE path=?',(path,))
    return {'files':len(ids),'assets':len(removed_assets)}
