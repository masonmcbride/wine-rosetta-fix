#!/usr/bin/env python3
"""Align endpoint samples using two exported signposts from the same PID.

Affine interpolation assumes clock behavior between anchors. Marker call brackets
are measured; they do not bound total alignment error or signpost transport delay.
"""
import argparse,csv,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET

def marker_times(path,pid):
    root=ET.parse(path).getroot();ids={x.attrib['id']:x for x in root.iter() if 'id' in x.attrib}
    def resolve(e):
        while e is not None and 'ref' in e.attrib:e=ids[e.attrib['ref']]
        return e
    found={}
    for row in root.iter('row'):
        process=resolve(row.find('process'))
        if process is None:continue
        p=resolve(process.find('pid'))
        if p is None or int(p.text)!=pid:continue
        subsystem=resolve(row.find('subsystem'));name=resolve(row.find('signpost-name'))
        if subsystem is None or subsystem.text!='com.mason.wine-profile' or name is None:continue
        if name.text not in ['WineSampleStart','WineSampleEnd']:continue
        if name.text in found:raise ValueError('Duplicate marker for PID')
        found[name.text]=int(resolve(row.find('event-time')).text)
    if set(found)!= {'WineSampleStart','WineSampleEnd'}:raise ValueError('Missing start/end marker for target PID')
    return found

def mapping(sync,markers):
    if not sync['start_marker_enabled'] or not sync['end_marker_enabled']:raise ValueError('Signpost collection was disabled')
    x0=(sync['start_marker_before']+sync['start_marker_after'])/2
    x1=(sync['end_marker_before']+sync['end_marker_after'])/2
    y0=markers['WineSampleStart'];y1=markers['WineSampleEnd']
    if x1<=x0 or y1<=y0:raise ValueError('Non-monotonic clock anchors')
    discrepancy_ns=(y1-y0)-(x1-x0)*1e9
    if abs(discrepancy_ns)>500000:raise ValueError('Anchor clocks disagree by over 0.5 ms; investigate before correlation')
    return x0,x1,y0,y1,discrepancy_ns

def align(samples,syncfile,signposts,output):
    sync=json.loads(syncfile.read_text());markers=marker_times(signposts,sync['pid']);x0,x1,y0,y1,drift=mapping(sync,markers)
    rows=written=outside=0
    with samples.open() as f,output.open('w',newline='') as dest:
        reader=csv.DictReader(f);writer=csv.DictWriter(dest,fieldnames=['trace_time_ns']+reader.fieldnames);writer.writeheader()
        for row in reader:
            rows+=1;x=sync['sample_start']+float(row['time'])
            if not x0<=x<=x1:outside+=1;continue
            row['trace_time_ns']=round(y0+(x-x0)/(x1-x0)*(y1-y0));writer.writerow(row);written+=1
    report={'pid':sync['pid'],'rows':rows,'aligned_rows':written,'outside_anchor_range':outside,'trace_start_marker_ns':y0,'trace_end_marker_ns':y1,'anchor_interval_difference_ns':drift,'start_marker_call_bracket_ns':(sync['start_marker_after']-sync['start_marker_before'])*1e9,'end_marker_call_bracket_ns':(sync['end_marker_after']-sync['end_marker_before'])*1e9,'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [samples,syncfile,signposts]},'limits':['Affine interpolation within two anchors; intermediate clock nonlinearity and signpost timestamp delay unmeasured','Marker brackets do not bound total alignment error','No extrapolation outside marker anchors','Location alignment is not exact function CPU cost or blocked duration']}
    Path(str(output)+'.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['samples','sync','signposts','output']:p.add_argument(name,type=Path)
    a=p.parse_args();print(json.dumps(align(a.samples,a.sync,a.signposts,a.output),indent=2))
