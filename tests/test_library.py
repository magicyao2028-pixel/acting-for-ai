import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('library', ROOT/'scripts/library.py')
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)


class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = lib.load_cards(ROOT)
        cls.sources = lib.read_json(ROOT/'sources/registry.json')
        cls.manifest = lib.read_json(ROOT/'manifest.json')

    def test_real_library_and_provenance(self):
        self.assertEqual([], lib.validate(self.cards,self.sources))
        self.assertEqual({'emotion','relationship','motion'}, {c['category'] for c in self.cards})

    def test_search_serves_chinese_and_english(self):
        self.assertEqual('请求许可/等待同意',lib.search(self.cards,'permission')[0]['title'])
        self.assertEqual('隐忍',lib.search(self.cards,'隐忍')[0]['title'])
        self.assertEqual([],lib.search(self.cards,'no-such-reference-9b17'))
        self.assertEqual([],lib.search(self.cards,' '))

    def test_search_filters_category_and_reads_guidance(self):
        relationships = lib.search(self.cards,'permission',category='relationship')
        self.assertTrue(relationships)
        self.assertTrue(all(card['category'] == 'relationship' for card in relationships))
        sample = copy.deepcopy(self.cards[0])
        sample['title'] = 'unrelated'
        sample['tags'] = []
        sample['channels'] = {}
        sample['prompt'] = ''
        sample['reference_text'] = ''
        sample['guidance'] = 'needle-only-guidance-term'
        self.assertEqual(sample['id'],lib.search([sample],'needle-only-guidance-term')[0]['id'])

    def test_search_payload_is_stable_and_traceable(self):
        payload = lib.search_payload(self.cards,'permission',limit=3,category='relationship')
        self.assertEqual(1,payload['schema_version'])
        self.assertEqual('relationship',payload['filters']['category'])
        self.assertLessEqual(payload['result_count'],3)
        self.assertEqual(payload['result_count'],len(payload['results']))
        first = payload['results'][0]
        self.assertEqual('REL-030',first['id'])
        self.assertEqual('cards/REL-030.json',first['json_path'])
        self.assertEqual('docs/cards/REL-030.md',first['markdown_path'])
        self.assertIn('status',first['validation'])

    def test_reject_duplicate_and_unbound_sources(self):
        bad = copy.deepcopy(self.cards[:2])
        bad[1]['id'] = bad[0]['id']
        bad[0]['source_ids'] = ['SRC-missing']
        errors = lib.validate(bad,self.sources)
        self.assertTrue(any('Duplicate ID' in e for e in errors))
        self.assertTrue(any('unknown source' in e for e in errors))

    def test_reject_false_test_claim_without_record(self):
        bad = copy.deepcopy(self.cards[:1])
        bad[0]['validation']['status'] = 'documented_generation_test'
        self.assertTrue(any('requires a record' in e for e in lib.validate(bad,self.sources)))

    def test_exports_are_deterministic_and_complete(self):
        a=lib.exports(self.cards,self.sources,self.manifest)
        self.assertEqual(a,lib.exports(self.cards,self.sources,self.manifest))
        for c in self.cards:
            self.assertIn(f"docs/cards/{c['id']}.md",a)
            self.assertIn(c['title'],a[f"docs/cards/{c['id']}.md"])


if __name__ == '__main__':
    unittest.main()
