"""
Live integration test for OllamaProvider.

This test requires:
1. Ollama service running: ollama serve
2. llama3 model pulled: ollama pull llama3

Usage:
    python tests/test_llm_live.py

    OR

    pytest tests/test_llm_live.py -v -s

Note: This connects to actual Ollama service (not mocked).
"""

from llm.ollama_provider import OllamaProvider
from config.settings import LLMConfig


def test_health_check():
    """Test health check with live Ollama service."""
    print("\n" + "="*80)
    print("TEST 1: Health Check")
    print("="*80)

    config = LLMConfig(
        provider="ollama",
        model="llama3"
    )

    provider = OllamaProvider(config)
    health = provider.health_check()

    print(f"\n✓ Health Status:")
    print(f"  Service Running:    {health['service_running']}")
    print(f"  Model Available:    {health['model_available']}")
    print(f"  Model Name:         {health['model_name']}")
    print(f"  Available Models:   {health['available_models']}")
    print(f"  Error:              {health['error']}")

    assert health['service_running'], "Ollama service not running. Start with: ollama serve"
    assert health['model_available'], f"Model {config.model} not found. Pull with: ollama pull {config.model}"

    print("\n✅ Health check passed!")
    return health


def test_simple_generation():
    """Test simple text generation."""
    print("\n" + "="*80)
    print("TEST 2: Simple Generation")
    print("="*80)

    config = LLMConfig(
        provider="ollama",
        model="llama3",
        temperature=0.7,
        max_tokens=256
    )

    provider = OllamaProvider(config)

    prompt = "List 5 backend developer skills"
    print(f"\n📝 Prompt: {prompt}")
    print("\n⏳ Generating... (this may take a few seconds)")

    response = provider.generate(prompt)

    print(f"\n✓ Response:\n{response}")

    assert response, "Response should not be empty"
    assert len(response) > 20, "Response should be substantial"

    print("\n✅ Simple generation passed!")
    return response


def test_generation_with_system_prompt():
    """Test generation with system prompt."""
    print("\n" + "="*80)
    print("TEST 3: Generation with System Prompt")
    print("="*80)

    config = LLMConfig(
        provider="ollama",
        model="llama3",
        temperature=0.5,
        max_tokens=200
    )

    provider = OllamaProvider(config)

    system_prompt = "You are a hiring manager at a top tech company. Be concise and professional."
    user_prompt = "What are the 3 most important skills for a Python developer?"

    print(f"\n👤 System Prompt: {system_prompt}")
    print(f"📝 User Prompt: {user_prompt}")
    print("\n⏳ Generating...")

    response = provider.generate(
        user_prompt,
        system_prompt=system_prompt
    )

    print(f"\n✓ Response:\n{response}")

    assert response, "Response should not be empty"

    print("\n✅ System prompt generation passed!")
    return response


def test_structured_output():
    """Test structured JSON output."""
    print("\n" + "="*80)
    print("TEST 4: Structured Output (JSON)")
    print("="*80)

    config = LLMConfig(
        provider="ollama",
        model="llama3",
        temperature=0.2,  # Lower for more consistent JSON
        max_tokens=256
    )

    provider = OllamaProvider(config)

    schema = {
        "skills": "list of 3 backend skills",
        "importance": "high/medium/low",
        "experience_years": "integer"
    }

    prompt = """
    Analyze backend developer requirements:

    Generate a JSON response with skills, importance level, and minimum experience.
    """

    print(f"\n📋 Schema: {schema}")
    print(f"📝 Prompt: {prompt.strip()}")
    print("\n⏳ Generating JSON... (this may take longer)")

    result = provider.generate_with_structured_output(
        prompt,
        output_schema=schema
    )

    print(f"\n✓ Structured Output:")
    print(f"  Skills:             {result.get('skills', 'N/A')}")
    print(f"  Importance:         {result.get('importance', 'N/A')}")
    print(f"  Experience Years:   {result.get('experience_years', 'N/A')}")

    assert isinstance(result, dict), "Result should be a dictionary"
    assert result.get('skills'), "Response should have skills"

    print("\n✅ Structured output passed!")
    return result


def test_validate_credentials():
    """Test credential validation."""
    print("\n" + "="*80)
    print("TEST 5: Validate Credentials")
    print("="*80)

    config = LLMConfig(
        provider="ollama",
        model="llama3"
    )

    provider = OllamaProvider(config)

    print("\n⏳ Validating credentials...")
    is_valid = provider.validate_credentials()

    print(f"\n✓ Validation Result: {is_valid}")

    assert is_valid, "Credentials should be valid"

    print("\n✅ Credential validation passed!")
    return is_valid


def test_custom_parameters():
    """Test generation with custom parameters."""
    print("\n" + "="*80)
    print("TEST 6: Custom Parameters")
    print("="*80)

    config = LLMConfig(
        provider="ollama",
        model="llama3",
        temperature=0.7,
        max_tokens=512,
        timeout=30
    )

    provider = OllamaProvider(config)

    # Override parameters for this request
    print("\n📝 Prompt: Generate a job description for a Python Developer")
    print("⚙️ Custom Parameters:")
    print("   temperature: 0.9 (more creative)")
    print("   max_tokens: 256")
    print("\n⏳ Generating...")

    response = provider.generate(
        "Generate a job description for a Python Developer",
        temperature=0.9,  # More creative
        max_tokens=256
    )

    print(f"\n✓ Response:\n{response}")

    assert response, "Response should not be empty"
    assert len(response) > 0, "Response should have content"

    print("\n✅ Custom parameters test passed!")
    return response


def main():
    """Run all live tests."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  OLLAMA PROVIDER - LIVE INTEGRATION TESTS".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    print("\n📋 Prerequisites:")
    print("  1. Ollama service running:  ollama serve")
    print("  2. llama3 model pulled:     ollama pull llama3")

    try:
        # Test 1: Health check
        test_health_check()

        # Test 2: Simple generation
        test_simple_generation()

        # Test 3: System prompt
        test_generation_with_system_prompt()

        # Test 4: Structured output
        test_structured_output()

        # Test 5: Credential validation
        test_validate_credentials()

        # Test 6: Custom parameters
        test_custom_parameters()

        # Summary
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\n🎉 OllamaProvider is working correctly with live Ollama service!")

    except ConnectionError as e:
        print("\n" + "="*80)
        print("❌ CONNECTION ERROR")
        print("="*80)
        print(f"\n{e}")
        print("\n⚠️  Make sure to:")
        print("   1. Start Ollama:  ollama serve")
        print("   2. Pull model:    ollama pull llama3")
        return False

    except RuntimeError as e:
        print("\n" + "="*80)
        print("❌ RUNTIME ERROR")
        print("="*80)
        print(f"\n{e}")
        print("\n⚠️  This might indicate:")
        print("   • Ollama service is slow")
        print("   • Model needs to be pulled: ollama pull llama3")
        print("   • System resources are low")
        return False

    except AssertionError as e:
        print("\n" + "="*80)
        print("❌ ASSERTION FAILED")
        print("="*80)
        print(f"\n{e}")
        return False

    except Exception as e:
        print("\n" + "="*80)
        print("❌ UNEXPECTED ERROR")
        print("="*80)
        print(f"\n{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
