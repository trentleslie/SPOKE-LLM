import unittest
from unittest.mock import patch, MagicMock
from arangodb_loader import ensure_collections, load_data_from_json, connect_to_arangodb, create_or_get_database, main

class TestArangoDBLoader(unittest.TestCase):

    @patch('arangodb_loader.Connection')
    def test_connect_to_arangodb(self, mock_connection):
        mock_connection.return_value = MagicMock()
        result = connect_to_arangodb('username', 'password')
        self.assertIsNotNone(result)
        mock_connection.assert_called_once_with(username='username', password='password')

    @patch('arangodb_loader.Connection')
    def test_connect_to_arangodb_failure(self, mock_connection):
        mock_connection.side_effect = ConnectionError("Connection failed")
        with patch('builtins.print') as mock_print:
            result = connect_to_arangodb('username', 'password')
        self.assertIsNone(result)
        mock_print.assert_called_once_with("Unable to establish connection, perhaps ArangoDB is not running: Connection failed")

    def test_create_or_get_database(self):
        mock_conn = MagicMock()
        mock_conn.hasDatabase.return_value = False
        result = create_or_get_database(mock_conn, 'test_db')
        mock_conn.createDatabase.assert_called_once_with(name='test_db')
        self.assertEqual(result, mock_conn['test_db'])

    def test_ensure_collections(self):
        mock_db = MagicMock()
        mock_db.hasCollection.side_effect = [False, False]
        ensure_collections(mock_db)
        mock_db.createCollection.assert_any_call(name="Nodes")
        mock_db.createCollection.assert_any_call(name="Edges", className="Edges", type=3)

    @patch('arangodb_loader.open')
    @patch('arangodb_loader.json.loads')
    def test_load_data_from_json(self, mock_json_loads, mock_open):
        mock_db = MagicMock()
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_file.__iter__.return_value = ['line1', 'line2']
        mock_json_loads.side_effect = [
            {'type': 'node', 'id': '1'},
            {'type': 'relationship', 'start': {'id': '1'}, 'end': {'id': '2'}}
        ]

        nodes_added, edges_added = load_data_from_json('test.json', mock_db)

        self.assertEqual(nodes_added, 1)
        self.assertEqual(edges_added, 1)
        mock_db['Nodes'].createDocument.assert_called_once()
        mock_db['Edges'].createDocument.assert_called_once()
        
        # Check that createDocument was called twice in total
        total_create_document_calls = mock_db['Nodes'].createDocument.call_count + mock_db['Edges'].createDocument.call_count
        self.assertEqual(total_create_document_calls, 2)

    @patch('arangodb_loader.connect_to_arangodb')
    @patch('arangodb_loader.create_or_get_database')
    @patch('arangodb_loader.ensure_collections')
    @patch('arangodb_loader.load_data_from_json')
    def test_main(self, mock_load_data, mock_ensure_collections, mock_create_or_get_db, mock_connect):
        mock_connect.return_value = MagicMock()
        mock_create_or_get_db.return_value = MagicMock()
        mock_load_data.return_value = (10, 20)

        with patch('builtins.print') as mock_print:
            main('test_db', 'test.json', 'username', 'password')

        mock_connect.assert_called_once_with('username', 'password')
        mock_create_or_get_db.assert_called_once()
        mock_ensure_collections.assert_called_once()
        mock_load_data.assert_called_once_with('test.json', mock_create_or_get_db.return_value)
        mock_print.assert_any_call("Total nodes added: 10")
        mock_print.assert_any_call("Total edges added: 20")

if __name__ == '__main__':
    unittest.main()
