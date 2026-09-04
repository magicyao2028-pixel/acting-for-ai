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
