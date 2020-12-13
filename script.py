import csv
import sys

#Convert CSV to array of dictionary
def csv_to_dict(file):
    with open(file) as f:
        dic = [{k: v for k, v in row.items()}
            for row in csv.DictReader(f, skipinitialspace=True)]
    return dic

districts = csv_to_dict(sys.argv[1])
labs = csv_to_dict(sys.argv[2])

districts_dic = {} #To access districts by ids
for i in districts:
    i['labs'] = [j for j in labs if i['district_id'] == j['district_id']]
    i['labs'].sort(key = lambda x: (x['lab_type'])) #This way we process govt labs before private labs 
    districts_dic[i['district_id']] = i

labs_rem = {} #Remaining testing capacity of lab
labs_excess = {} #Remaining excess storage capacity of lab (initially 100)
district_rem = {} #Remaining samples to be allocated 
labs_loc = {} #Dictionary to access location of labs
district_loc = {} #Dictionary to access location of districts
for i in districts:
    district_rem[i['district_id']] = int(i['samples']) 
    district_loc[i['district_id']] = {'lat': float(i['lat']), 'lon': float(i['lon'])} 
for i in labs:
    labs_rem[i['id']] = int(i['capacity']) - int(i['backlogs']) 
    labs_excess[i['id']] = 100
    labs_loc[i['id']] = {'lat': float(i['lat']), 'lon': float(i['lon']), 'lab_type': int(i['lab_type'])}
    
output = [] #Store output
transfers_dict = {} #Store total samples transferred from district i to lab j
for i in districts:
    for j in labs:
        transfers_dict[tuple([i['district_id'], j['id']])] = 0 #Initiate samples tranferred with 0

#For each district, distribute all samples to its lab order by lab_type(first govt then private labs)
for i in districts:
    for j in i['labs']:
        if district_rem[i['district_id']] <= labs_rem[j['id']]:
            labs_rem[j['id']] -= district_rem[i['district_id']]
            transfers_dict[tuple([i['district_id'], j['id']])] += district_rem[i['district_id']] 
            del district_rem[i['district_id']] #Remove from dictionary if all samples allocated
            if not labs_rem[j['id']]:
                del labs_rem[j['id']]
            break
        district_rem[i['district_id']] -= labs_rem[j['id']]
        transfers_dict[tuple([i['district_id'], j['id']])] += labs_rem[j['id']]
        del labs_rem[j['id']] #Remove from dictionary if total samples transferred to lab is equal to its capacity 

#Calculate distance (in kms) between two locations
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

lab_sets = {} #To store set of labs which are in reach of 40km from each other

def isCompatible(cur_set, lab_id):
    #Return True if and only if lab with id=lab_id has distance less than 40kms from each of the labs present in cur_set
    for i in cur_set:
        i = str(i)
        if calc_dis(labs_loc[i]['lat'], labs_loc[i]['lon'], labs_loc[lab_id]['lat'], labs_loc[lab_id]['lon']) >= 40.0:
            return 0 
    return 1

#Generate Sets using recursion
def generate_sets(cur_set, cur_list):
    #cur_set contains current set of labs which are in reach of 40kms from each other
    #cur_list contains list of labs which can possibly be added to cur_set 
    if cur_set in lab_sets: 
        return #If this set already processed in previous recursions then return 
    lab_sets[cur_set] = 1 #Add current set of labs(cur_set) to lab_sets
    new_cur_list = [j for j in cur_list if isCompatible(cur_set, str(j))] #Generate new list of labs which are compatible with cur_set
    for j in new_cur_list:
        tmp_cur_set = list(cur_set)
        tmp_cur_set.append(j) 
        tmp_cur_set.sort() #Sort to maintain uniformity, hence set [1, 2, 3] and set[2, 1, 3] are equivalent
        generate_sets(tuple(tmp_cur_set), tuple([k for k in new_cur_list if k != j])) #Recurse by adding one lab at a time to cur_set

cur_list = list(labs_rem.keys())
#Initiate recursion by adding each lab to cur_set and rest of them to cur_list
for i in cur_list:
    generate_sets(tuple([int(i)]), tuple([int(j) for j in cur_list if j != i]))

def calc_centroid(labs_used):   
    #Centroid is calculated by taking arithmetic mean of latitudes and longitudes of labs present in list "labs_used"
    x = 0.0 
    y = 0.0
    for i in labs_used:
        x += labs_loc[str(i)]['lat']
        y += labs_loc[str(i)]['lon']
    x /= len(labs_used)
    y /= len(labs_used)
    return (x, y)

def calc_cost(dist_id, cur_labs):
    rem = district_rem[dist_id] #Remaining samples to be allocated
    used = [] #Contains list of labs used to allocate samples
    cost = 0.0 #Initial cost = 0

    #Tranfer samples to labs for testing
    for i in cur_labs:
        used.append(i)
        x = min(rem, labs_rem[str(i)]) #No. of samples allocated to lab "i"
        rem -= x
        cost += x * (800, 1600)[labs_loc[str(i)]['lab_type']] #800 for govt labs / 1600 for private labs
        if not rem: #Break if all samples allocated
            break
    centroid = calc_centroid(used)

    #Tranfer samples to labs for storage (backlogs)
    for i in districts_dic[dist_id]['labs']:
        if not rem:
            break
        cost += min(rem, labs_excess[i['id']]) * 5000 #Cost 5000 per sample
        rem -= min(rem, labs_excess[i['id']])

    return (cost + rem * 10000.0 + 1000.0 * calc_dis(centroid[0], centroid[1], district_loc[dist_id]['lat'], district_loc[dist_id]['lon']), tuple(used)) #Total cost = cost + ((no. of samples still not allocated (rem)) * 10000) + (Travel cost = 1000 * distance between district and centroid of labs used) 
    

#Remove keys from lab_set if samples are allocated to its full capacity
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
    cost = 10000.0 * district_rem[i] #Initiate cost with a large number
    labs_used = [] #This will store the set of labs which will result in minimum cost

    #Try each set of labs present in lab_sets
    for j in lab_sets.keys():
        cur_cost = calc_cost(i, j)
        if cost > cur_cost[0]: #If current set of lab result in less cost, then assign "cur_cost" with the cost and "labs_used" with the current set of lab
            cost = cur_cost[0]
            labs_used = cur_cost[1]
    to_rem = [] #Store list of labs which are fully allocated to their capacity
    for j in labs_used:
        j = str(j)
        x = min(district_rem[i], labs_rem[j]) #Samples to be allocated
        district_rem[i] -= x 
        labs_rem[j] -= x
        transfers_dict[tuple([i, j])] += x
        if not labs_rem[j]:
            to_rem.append(int(j)) #Add to "to_rem" if no space left in current lab
    
    for j in districts_dic[i]['labs']:
        if not district_rem[i]:
            break
        if labs_excess[j['id']]: #If excess space is left for backlog
            x = min(district_rem[i], labs_excess[j['id']])
            district_rem[i] -= x
            labs_excess[j['id']] -= x
            transfers_dict[tuple([i, j])] += x
    
    if district_rem[i]: #Allocate rest of samples to headquarters
        output.append({'transfer_type': 1, 'source': i, 'destination': i, 'samples_transferred': district_rem[i]})
    remove_keys(to_rem)

#Generate output from transfers_dict
for i in transfers_dict.keys():
    if transfers_dict[i]:
        output.append({'transfer_type': 0, 'source': i[0], 'destination': i[1], 'samples_transferred': transfers_dict[i]})

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
