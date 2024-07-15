import json
from tqdm import tqdm
from pyArango.connection import Connection
from pyArango.collection import Edges
from pyArango.theExceptions import CreationError

def ensure_collections(db):
    """Ensure the collections exist and are of correct type."""
    if not db.hasCollection("Nodes"):
        db.createCollection(name="Nodes")
    if not db.hasCollection("Edges"):
        # Specify the name for the edge collection
        db.createCollection(name="Edges", className="Edges", type=3)

def load_data_from_json(filename, db, stop_at=-1):
    """Load data from JSON file into the database."""
    nodes_added = 0
    edges_added = 0

    with open(filename, 'r') as file:
        total_lines = sum(1 for line in file)
        file.seek(0)  # Reset file read position
        
        for line in tqdm(file, total=total_lines, desc="Loading Data"):
            if stop_at > -1 and (nodes_added + edges_added) >= stop_at:
                break
            
            try:
                data = json.loads(line)
                if data['type'] == 'node':
                    node_doc = db["Nodes"].createDocument()
                    node_doc['_key'] = str(data['id'])
                    node_doc.set(data)
                    node_doc.save()
                    nodes_added += 1
                elif data['type'] == 'relationship':
                    edge_doc = db["Edges"].createDocument()
                    edge_doc['_from'] = 'Nodes/' + str(data['start']['id'])
                    edge_doc['_to'] = 'Nodes/' + str(data['end']['id'])
                    # Copy other properties
                    for key, value in data.items():
                        if key not in ['_from', '_to', 'type', 'id']:
                            edge_doc[key] = value
                    edge_doc.save()
                    edges_added += 1
            except CreationError as e:
                if 'unique constraint violated' in e.message:
                    print(f"A document with _key {data['id']} already exists. Skipping...")
                else:
                    print(f"Failed to create document: {e}")
                continue
            except json.JSONDecodeError:
                continue  # Skip invalid JSON lines

    return nodes_added, edges_added

def connect_to_arangodb(username, password):
    """Connect to ArangoDB and return the connection object."""
    try:
        conn = Connection(username=username, password=password)
        return conn
    except ConnectionError as e:
        print(f"Unable to establish connection, perhaps ArangoDB is not running: {e}")
        return None

def create_or_get_database(conn, db_name):
    """Create a new database if it doesn't exist, or get the existing one."""
    if not conn.hasDatabase(db_name):
        conn.createDatabase(name=db_name)
    return conn[db_name]

def main(db_name, file_path, username, password):
    """Main function to orchestrate the data loading process."""
    print("Connecting...")
    conn = connect_to_arangodb(username, password)
    if not conn:
        return

    db = create_or_get_database(conn, db_name)
    ensure_collections(db)

    nodes_added, edges_added = load_data_from_json(file_path, db)

    print(f"Total nodes added: {nodes_added}")
    print(f"Total edges added: {edges_added}")

if __name__ == "__main__":
    # Example usage
    db_name = "spoke23_human"
    file_path = '/path/to/your/spoke_2023_human.json'
    username = "root"
    password = "your_password_here"
    main(db_name, file_path, username, password)
