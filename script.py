import csv
import sys

def csv_to_dict(file):
    with open(file) as f:
        dic = [{k: v for k, v in row.items()}
            for row in csv.DictReader(f, skipinitialspace=True)]
    return dic

districts = csv_to_dict(sys.argv[1])
labs = csv_to_dict(sys.argv[2])

districts_dic = {}
for i in districts:
    i['labs'] = [j for j in labs if i['district_id'] == j['district_id']]
    i['labs'].sort(key = lambda x: (x['lab_type']))
    districts_dic[i['district_id']] = i

labs_rem = {}
labs_excess = {}
district_rem = {}
labs_loc = {}
district_loc = {}
for i in districts:
    district_rem[i['district_id']] = int(i['samples']) 
    district_loc[i['district_id']] = {'lat': float(i['lat']), 'lon': float(i['lon'])} 
for i in labs:
    labs_rem[i['id']] = int(i['capacity']) - int(i['backlogs']) 
    labs_excess[i['id']] = 100
    labs_loc[i['id']] = {'lat': float(i['lat']), 'lon': float(i['lon']), 'lab_type': int(i['lab_type'])}
    
output = []
for i in districts:
    for j in i['labs']:
        if district_rem[i['district_id']] <= labs_rem[j['id']]:
            labs_rem[j['id']] -= district_rem[i['district_id']]
            output.append({'transfer_type': 0, 'source': i['district_id'], 'destination': j['id'], 'samples_transferred': district_rem[i['district_id']]})
            del district_rem[i['district_id']]
            if not labs_rem[j['id']]:
                del labs_rem[j['id']]
            break
        district_rem[i['district_id']] -= labs_rem[j['id']]
        output.append({'transfer_type': 0, 'source': i['district_id'], 'destination': j['id'], 'samples_transferred': labs_rem[j['id']]})
        del labs_rem[j['id']]

from math import sin, cos, sqrt, atan2, radians
def calc_dis(lat1, lon1, lat2, lon2):
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return 6373.0 * c

lab_sets = {}
def isCompatible(cur_set, lab_id):
    for i in cur_set:
        i = str(i)
        if calc_dis(labs_loc[i]['lat'], labs_loc[i]['lon'], labs_loc[lab_id]['lat'], labs_loc[lab_id]['lon']) >= 40.0:
            return 0
    return 1

def generate_sets(cur_set, cur_list):
    if cur_set in lab_sets:
        return
    lab_sets[cur_set] = 1
    new_cur_list = [j for j in cur_list if isCompatible(cur_set, str(j))]
    for j in new_cur_list:
        tmp_cur_set = list(cur_set)
        tmp_cur_set.append(j)
        tmp_cur_set.sort()
        generate_sets(tuple(tmp_cur_set), tuple([k for k in new_cur_list if k != j]))

cur_list = list(labs_rem.keys())
for i in cur_list:
    generate_sets(tuple([int(i)]), tuple([int(j) for j in cur_list if j != i]))

def calc_centroid(labs_used):
    x = 0.0 
    y = 0.0
    for i in labs_used:
        x += labs_loc[str(i)]['lat']
        y += labs_loc[str(i)]['lon']
    x /= len(labs_used)
    y /= len(labs_used)
    return (x, y)
def calc_cost(dist_id, cur_labs):
    rem = district_rem[dist_id]
    used = []
    cost = 0.0
    for i in cur_labs:
        used.append(i)
        x = min(rem, labs_rem[str(i)])
        rem -= x
        cost += x * (800, 1600)[labs_loc[str(i)]['lab_type']]
        if not rem:
            break
    centroid = calc_centroid(used)
    for i in districts_dic[dist_id]['labs']:
        cost += min(rem, labs_excess[i['id']]) * 5000
        rem -= min(rem, labs_excess[i['id']])
        if not rem:
            break
    return (cost + rem * 10000.0 + 1000.0 * calc_dis(centroid[0], centroid[1], district_loc[dist_id]['lat'], district_loc[dist_id]['lon']), tuple(used))
    
def remove_keys(to_rem):
    keys_rem = []
    for i in lab_sets.keys():
        for j in to_rem:
            if j in i:
                keys_rem.append(i)
                break
    for i in keys_rem:
        del lab_sets[i]

for i in district_rem.keys():
    i = str(i)
    cost = 10000.0 * district_rem[i]
    labs_used = []
    for j in lab_sets.keys():
        cur_cost = calc_cost(i, j)
        if cost > cur_cost[0]:
            cost = cur_cost[0]
            labs_used = cur_cost[1]
    to_rem = []
    for j in labs_used:
        j = str(j)
        x = min(district_rem[i], labs_rem[j])
        district_rem[i] -= x
        labs_rem[j] -= x
        output.append({'transfer_type': 0, 'source': i, 'destination': j, 'samples_transferred': x})
        if not labs_rem[j]:
            to_rem.append(int(j))
    
    for j in districts_dic[dist_id]['labs']:
        if not district_rem[i]:
            break
        if labs_excess[j['id']]:
            x = min(district_rem[i], labs_excess[j['id']])
            district_rem[i] -= x
            labs_excess[j['id']] -= x
            output.append({'transfer_type': 0, 'source': i, 'destination': j['id'], 'samples_transferred': x})
    
    if district_rem[i]:
        output.append({'transfer_type': 1, 'source': i, 'destination': i, 'samples_transferred': district_rem[i]})
    remove_keys(to_rem)

#Create JSON output
import json 
with open('output.json', 'w') as outfile:
    json.dump(output, outfile)

#Create CSV output
field_names = ['transfer_type', 'source', 'destination', 'samples_transferred'] 
with open('Output.csv', 'w') as csvfile: 
    writer = csv.DictWriter(csvfile, fieldnames = field_names) 
    writer.writeheader() 
    writer.writerows(output) 
