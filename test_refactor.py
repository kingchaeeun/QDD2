"""
Simple test script to verify refactoring works correctly.
"""

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        from quote_backend.core.pipeline import build_queries_from_text
        from quote_backend.utils.translation import translate_ko_to_en
        from quote_backend.services.quote_service import QuoteService
        from quote_backend.services.search_service import SearchService
        from quote_backend.config import GOOGLE_API_KEY, API_PORT
        print("✅ All new imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    try:
        # Test backward compatibility
        from app.pipeline import build_queries_from_text as old_build
        from app.translation import translate_ko_to_en as old_translate
        print("✅ Backward compatibility imports successful")
    except ImportError as e:
        print(f"⚠️  Backward compatibility warning: {e}")
    
    return True


def test_basic_functionality():
    """Test basic functionality without requiring models."""
    print("\nTesting basic functionality...")
    
    try:
        from quote_backend.utils.text_utils import extract_quotes, split_sentences
        
        test_text = '트럼프가 "베네수엘라 상공 전면폐쇄"라고 발표했다.'
        quotes = extract_quotes(test_text)
        sentences = split_sentences(test_text)
        
        assert len(quotes) > 0, "Should extract at least one quote"
        assert len(sentences) > 0, "Should split into sentences"
        print("✅ Basic text utilities work correctly")
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Refactoring Verification Test")
    print("=" * 50)
    
    success = True
    success &= test_imports()
    success &= test_basic_functionality()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 50)

